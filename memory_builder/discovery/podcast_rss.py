from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import httpx

from memory_builder.discovery.seed_links import classify_source_type, infer_media_format, infer_source_nature, is_processable_source
from memory_builder.discovery.source_emit import OnSourceRecord
from memory_builder.discovery.watermarks import is_newer_than
from memory_builder.models import SourceRecord, SourceStatus
from memory_builder.telemetry.discovery_events import discovery_log
from memory_builder.storage.sqlite_store import normalize_url


APPLE_PODCAST_ID_PATTERN = re.compile(r"/podcast/[^/]+/id(\d+)", re.IGNORECASE)
SPOTIFY_SHOW_ID_PATTERN = re.compile(r"open\.spotify\.com/show/([A-Za-z0-9]+)")


def resolve_apple_podcast_rss(apple_podcast_url: str) -> tuple[str | None, str | None]:
    match = APPLE_PODCAST_ID_PATTERN.search(apple_podcast_url)
    if not match:
        return None, None
    podcast_id = match.group(1)
    try:
        response = httpx.get(
            f"https://itunes.apple.com/lookup?id={podcast_id}",
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None, podcast_id
    results = payload.get("results") or []
    if not results:
        return None, podcast_id
    return results[0].get("feedUrl"), podcast_id


def resolve_spotify_show_rss(spotify_show_url: str, *, search_term: str | None = None) -> tuple[str | None, str | None]:
    show_match = SPOTIFY_SHOW_ID_PATTERN.search(spotify_show_url)
    if not show_match:
        return None, None

    show_title = search_term
    if not show_title:
        try:
            response = httpx.get(spotify_show_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
            if og_title:
                show_title = og_title.group(1).strip()
        except httpx.HTTPError:
            show_title = None

    if not show_title:
        return None, None

    try:
        response = httpx.get(
            "https://itunes.apple.com/search",
            params={"term": show_title, "entity": "podcast", "limit": 5},
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None, None

    normalized_target = _normalize_show_name(show_title)
    for result in payload.get("results") or []:
        candidate_name = result.get("collectionName") or result.get("trackName") or ""
        if _normalize_show_name(candidate_name) == normalized_target:
            return result.get("feedUrl"), str(result.get("collectionId") or "")
        if normalized_target and normalized_target in _normalize_show_name(candidate_name):
            return result.get("feedUrl"), str(result.get("collectionId") or "")
    results = payload.get("results") or []
    if results:
        return results[0].get("feedUrl"), str(results[0].get("collectionId") or "")
    return None, None


def _normalize_show_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _entry_link(entry: feedparser.FeedParserDict) -> str:
    link = getattr(entry, "link", None)
    if link:
        return normalize_url(link)
    for item in getattr(entry, "links", []) or []:
        href = item.get("href")
        if href and item.get("rel") == "alternate":
            return normalize_url(href)
    for item in getattr(entry, "links", []) or []:
        href = item.get("href")
        if href and item.get("rel") == "enclosure":
            return normalize_url(href)
    entry_id = getattr(entry, "id", None)
    if entry_id:
        return normalize_url(f"podcast-entry:{entry_id}")
    return ""


def _entry_published_iso(entry: feedparser.FeedParserDict) -> str | None:
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
    if getattr(entry, "updated_parsed", None):
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
    return None



def discover_podcast_rss_feed(
    persona_id: str,
    feed_url: str,
    *,
    channel_url: str,
    seen: set[str],
    watermark: str | None = None,
    on_record: OnSourceRecord | None = None,
) -> tuple[list[SourceRecord], str | None]:
    watermark_note = f" (watermark: {watermark[:10]})" if watermark else " (watermark: nincs)"
    discovery_log(f"Podcast RSS: feed beolvasása{watermark_note} — {feed_url}")
    parsed = feedparser.parse(feed_url)
    records: list[SourceRecord] = []
    max_published: str | None = watermark
    for entry in parsed.entries:
        link = _entry_link(entry)
        if not link or link in seen:
            continue
        published = _entry_published_iso(entry)
        if not is_newer_than(published, watermark):
            continue
        if not is_processable_source(link) and not link.startswith("podcast-entry:"):
            if not any(token in link for token in ("episode.flightcast.com", ".mp3", ".m4a")):
                continue
        seen.add(link)
        source_type = classify_source_type(link)
        if link.startswith("podcast-entry:") or urlparse(link).path.endswith((".mp3", ".m4a")):
            source_type = classify_source_type("https://open.spotify.com/episode/example")
        title = getattr(entry, "title", link) or link
        record = SourceRecord(
            persona_id=persona_id,
            source_url=link,
            source_title=title,
            source_type=source_type,
            source_date=published,
            source_nature=infer_source_nature(source_type, link),
            media_format=infer_media_format(source_type, link),
            status=SourceStatus.PENDING,
            channel_url=channel_url,
        )
        if published and (max_published is None or published > max_published):
            max_published = published
        if on_record is not None:
            if not on_record(record):
                break
        records.append(record)
    discovery_log(f"Podcast RSS: {len(records)} epizód — {feed_url}")
    return records, max_published
