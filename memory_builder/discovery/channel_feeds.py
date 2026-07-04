from __future__ import annotations

from datetime import datetime, timezone

from collections.abc import Callable

from memory_builder.channel_registry import ContentChannel, ChannelRegistry, sorted_channels
from memory_builder.dedup.title_dedup import should_skip_podcast_for_youtube_duplicate
from memory_builder.discovery.podcast_rss import (
    discover_podcast_rss_feed,
    resolve_apple_podcast_rss,
    resolve_spotify_show_rss,
)
from memory_builder.discovery.source_emit import OnSourceRecord
from memory_builder.discovery.web_feeds import _discover_web_links, _parse_rss_feed, youtube_channel_rss
from memory_builder.discovery.youtube_ytdlp import discover_youtube_channel_ytdlp
from memory_builder.discovery.watermarks import bootstrap_channel_watermark
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.pipeline.platform_filter import channel_matches_platform
from memory_builder.telemetry.discovery_events import discovery_log


def _resolve_channel_rss(channel: ContentChannel) -> str | None:
    if channel.rss_url:
        return channel.rss_url
    if channel.type == "apple_podcast":
        rss_url, podcast_id = resolve_apple_podcast_rss(channel.url)
        if podcast_id:
            channel.apple_podcast_id = podcast_id
        return rss_url
    if channel.type == "spotify_show":
        rss_url, podcast_id = resolve_spotify_show_rss(channel.url, search_term=channel.label or None)
        if podcast_id:
            channel.apple_podcast_id = podcast_id
        return rss_url
    if channel.type == "podcast_rss":
        return channel.url
    return None


def discover_channel(
    persona_id: str,
    channel: ContentChannel,
    seen: set[str],
    *,
    store: SQLiteStore | None = None,
    on_record: OnSourceRecord | None = None,
) -> tuple[list[SourceRecord], str | None]:
    watermark = bootstrap_channel_watermark(store, channel.url, channel.latest_published_at)
    records: list[SourceRecord] = []
    latest_published: str | None = watermark

    def track(record: SourceRecord) -> bool:
        nonlocal latest_published
        if record.source_date and (
            latest_published is None or record.source_date > latest_published
        ):
            latest_published = record.source_date
        if not record.channel_url:
            record.channel_url = channel.url
        if store is not None and record.source_type == SourceType.PODCAST:
            conn = store.connect()
            skip, reason = should_skip_podcast_for_youtube_duplicate(
                conn, persona_id, record.source_title
            )
            if skip:
                record.status = SourceStatus.SKIPPED
                record.error_message = reason
        if on_record is not None:
            return on_record(record)
        records.append(record)
        return True

    emit = track if on_record is not None else None

    if channel.type == "youtube_channel":
        batch = discover_youtube_channel_ytdlp(
            persona_id,
            channel.url,
            seen,
            watermark=watermark,
            channel_url_meta=channel.url,
            on_record=emit,
        )
        if on_record is None:
            records = batch
            for record in records:
                record.channel_url = record.channel_url or channel.url
            if not records:
                rss_url = youtube_channel_rss(channel.url)
                if rss_url:
                    records = _parse_rss_feed(
                        persona_id,
                        rss_url,
                        seen,
                        watermark=watermark,
                        channel_url=channel.url,
                        on_record=emit,
                    )
        elif not batch:
            rss_url = youtube_channel_rss(channel.url)
            if rss_url:
                _parse_rss_feed(
                    persona_id,
                    rss_url,
                    seen,
                    watermark=watermark,
                    channel_url=channel.url,
                    on_record=emit,
                )
        max_published = latest_published or watermark
        return records, max_published

    if channel.type == "web_site":
        batch = _discover_web_links(
            persona_id,
            channel.url,
            seen,
            store=store,
            watermark=watermark,
            on_record=emit,
        )
        if on_record is None:
            records = batch
            for record in records:
                record.channel_url = record.channel_url or channel.url
        max_published = latest_published or watermark
        return records, max_published

    rss_url = _resolve_channel_rss(channel)
    if not rss_url:
        return [], watermark
    channel.rss_url = rss_url
    batch, max_published = discover_podcast_rss_feed(
        persona_id,
        rss_url,
        channel_url=channel.url,
        seen=seen,
        watermark=watermark,
        on_record=emit,
    )
    if on_record is None:
        records = batch
    return records, max_published or latest_published or watermark


def discover_channels(
    persona_id: str,
    registry: ChannelRegistry,
    *,
    channel_ids: list[str] | None = None,
    store: SQLiteStore | None = None,
    only_platform: str | None = None,
    on_record: OnSourceRecord | None = None,
    after_channel: Callable[[], None] | None = None,
) -> list[SourceRecord]:
    discovered: list[SourceRecord] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()
    stop_all = False

    def track(record: SourceRecord) -> bool:
        nonlocal stop_all
        if on_record is None:
            discovered.append(record)
            return True
        if not on_record(record):
            stop_all = True
            return False
        return True

    emit = track if on_record is not None else None

    for channel in sorted_channels(registry):
        if stop_all:
            break
        if channel_ids and channel.channel_id not in channel_ids:
            continue
        if not channel_matches_platform(channel, only_platform):
            continue
        label = channel.label or channel.url
        old_watermark = bootstrap_channel_watermark(store, channel.url, channel.latest_published_at)
        watermark_note = (
            f" (watermark: {old_watermark[:10]})"
            if old_watermark
            else " (watermark: nincs)"
        )
        discovery_log(f"Csatorna [{channel.type}]: {label}{watermark_note}")
        records, max_published = discover_channel(
            persona_id,
            channel,
            seen,
            store=store,
            on_record=emit,
        )
        if on_record is None:
            discovered.extend(records)
        channel.last_discovered_at = now
        if max_published and (
            channel.latest_published_at is None or max_published > channel.latest_published_at
        ):
            channel.latest_published_at = max_published
        elif old_watermark and channel.latest_published_at is None:
            channel.latest_published_at = old_watermark
        suffix = f", watermark → {max_published[:10]}" if max_published else ""
        if on_record is None:
            discovery_log(f"Csatorna [{channel.type}]: {label} — {len(records)} jelölt{suffix}")
        else:
            discovery_log(f"Csatorna [{channel.type}]: {label} — kész{suffix}")
        if after_channel is not None:
            after_channel()
    return discovered


def processing_priority(source_type: str) -> int:
    if source_type == SourceType.YOUTUBE:
        return 1
    if source_type == SourceType.PODCAST:
        return 2
    return 3
