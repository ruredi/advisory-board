from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import feedparser
import httpx

from memory_builder.discovery.seed_links import classify_source_type, infer_source_nature, is_processable_source
from memory_builder.discovery.youtube_ytdlp import resolve_youtube_channel_id_ytdlp
from memory_builder.models import SourceRecord, SourceStatus
from memory_builder.storage.sqlite_store import normalize_url


log = logging.getLogger(__name__)


YOUTUBE_CHANNEL_ID_PATTERN = re.compile(r'"channelId":"(UC[^"]+)"|itemprop="channelId" content="(UC[^"]+)"')


def discover_watch_feeds(persona_id: str, watch_feeds: list[dict[str, str]]) -> list[SourceRecord]:
    discovered: list[SourceRecord] = []
    seen: set[str] = set()
    for feed in watch_feeds:
        feed_type = feed.get("type", "rss")
        url = feed.get("url", "")
        if not url:
            continue
        if feed_type == "youtube_channel":
            rss_url = youtube_channel_rss(url)
            if rss_url:
                discovered.extend(_parse_rss_feed(persona_id, rss_url, seen))
        elif feed_type in {"rss", "web"}:
            rss_url = url if feed_type == "rss" else None
            if rss_url:
                discovered.extend(_parse_rss_feed(persona_id, rss_url, seen))
            elif feed_type == "web":
                discovered.extend(_discover_web_links(persona_id, url, seen))
    return discovered


def youtube_channel_rss(channel_url: str) -> str | None:
    if "channel_id=" in channel_url:
        return channel_url
    if "/feeds/videos.xml" in channel_url:
        return channel_url
    try:
        response = httpx.get(channel_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    match = YOUTUBE_CHANNEL_ID_PATTERN.search(response.text)
    if match:
        channel_id = next(group for group in match.groups() if group)
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    channel_id = resolve_youtube_channel_id_ytdlp(channel_url)
    if channel_id:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    return None


def _parse_rss_feed(
    persona_id: str,
    feed_url: str,
    seen: set[str],
    *,
    watermark: str | None = None,
    channel_url: str | None = None,
) -> list[SourceRecord]:
    parsed = feedparser.parse(feed_url)
    records: list[SourceRecord] = []
    for entry in parsed.entries:
        link = normalize_url(getattr(entry, "link", "") or "")
        if not link or link in seen:
            continue
        if not is_processable_source(link):
            continue
        published = None
        if getattr(entry, "published_parsed", None):
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        if watermark and published and published <= watermark:
            continue
        seen.add(link)
        source_type = classify_source_type(link)
        records.append(
            SourceRecord(
                persona_id=persona_id,
                source_url=link,
                source_title=getattr(entry, "title", link),
                source_type=source_type,
                source_date=published,
                source_nature=infer_source_nature(source_type, link),
                status=SourceStatus.PENDING,
                channel_url=channel_url,
            )
        )
    return records


def _discover_web_links(persona_id: str, page_url: str, seen: set[str]) -> list[SourceRecord]:
    try:
        response = httpx.get(page_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return []
    links = re.findall(r'href="(https?://[^"]+)"', response.text)
    records: list[SourceRecord] = []
    host = urlparse(page_url).netloc.lower()
    for link in links:
        normalized = normalize_url(link)
        if normalized in seen:
            continue
        if urlparse(normalized).netloc.lower().endswith(host.removeprefix("www.")) or "acquisition.com" in normalized:
            if not is_processable_source(normalized):
                continue
            seen.add(normalized)
            source_type = classify_source_type(normalized)
            records.append(
                SourceRecord(
                    persona_id=persona_id,
                    source_url=normalized,
                    source_title=normalized,
                    source_type=source_type,
                    source_nature=infer_source_nature(source_type, normalized),
                    status=SourceStatus.PENDING,
                )
            )
    return records
