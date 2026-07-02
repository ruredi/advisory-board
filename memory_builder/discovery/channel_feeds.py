from __future__ import annotations

from datetime import datetime, timezone

from memory_builder.channel_registry import ContentChannel, ChannelRegistry, sorted_channels
from memory_builder.discovery.podcast_rss import (
    discover_podcast_rss_feed,
    resolve_apple_podcast_rss,
    resolve_spotify_show_rss,
)
from memory_builder.discovery.web_feeds import _parse_rss_feed, youtube_channel_rss
from memory_builder.discovery.youtube_ytdlp import discover_youtube_channel_ytdlp
from memory_builder.dedup.title_dedup import normalize_episode_title, should_skip_podcast_for_youtube_duplicate
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import SQLiteStore


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
) -> tuple[list[SourceRecord], str | None]:
    watermark = channel.latest_published_at
    if channel.type == "youtube_channel":
        records = discover_youtube_channel_ytdlp(
            persona_id,
            channel.url,
            seen,
            watermark=watermark,
            channel_url_meta=channel.url,
        )
        if not records:
            rss_url = youtube_channel_rss(channel.url)
            if rss_url:
                records = _parse_rss_feed(
                    persona_id,
                    rss_url,
                    seen,
                    watermark=watermark,
                    channel_url=channel.url,
                )
        for record in records:
            if not record.channel_url:
                record.channel_url = channel.url
        max_published = _max_source_date(records) or watermark
        return records, max_published

    rss_url = _resolve_channel_rss(channel)
    if not rss_url:
        return [], watermark
    channel.rss_url = rss_url
    records, max_published = discover_podcast_rss_feed(
        persona_id,
        rss_url,
        channel_url=channel.url,
        seen=seen,
        watermark=watermark,
    )
    if store is not None:
        conn = store.connect()
        filtered: list[SourceRecord] = []
        for record in records:
            skip, reason = should_skip_podcast_for_youtube_duplicate(conn, persona_id, record.source_title)
            if skip:
                record.status = SourceStatus.SKIPPED
                record.error_message = reason
            filtered.append(record)
        records = filtered
    return records, max_published


def discover_channels(
    persona_id: str,
    registry: ChannelRegistry,
    *,
    channel_ids: list[str] | None = None,
    store: SQLiteStore | None = None,
) -> list[SourceRecord]:
    discovered: list[SourceRecord] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()
    for channel in sorted_channels(registry):
        if channel_ids and channel.channel_id not in channel_ids:
            continue
        records, max_published = discover_channel(persona_id, channel, seen, store=store)
        discovered.extend(records)
        channel.last_discovered_at = now
        if max_published and (channel.latest_published_at is None or max_published > channel.latest_published_at):
            channel.latest_published_at = max_published
    return discovered


def _max_source_date(records: list[SourceRecord]) -> str | None:
    dates = [record.source_date for record in records if record.source_date]
    return max(dates) if dates else None


def processing_priority(source_type: str) -> int:
    if source_type == SourceType.YOUTUBE:
        return 1
    if source_type == SourceType.PODCAST:
        return 2
    return 3
