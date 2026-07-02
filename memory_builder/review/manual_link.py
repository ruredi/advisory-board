from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from memory_builder.channel_registry import add_channel
from memory_builder.discovery.podcast_rss import resolve_apple_podcast_rss, resolve_spotify_show_rss
from memory_builder.discovery.profile_urls import canonicalize_profile_url, classify_platform
from memory_builder.storage.sqlite_store import normalize_url


SPOTIFY_SHOW_PATTERN = re.compile(r"open\.spotify\.com/show/([A-Za-z0-9]+)", re.IGNORECASE)
APPLE_PODCAST_PATTERN = re.compile(r"podcasts\.apple\.com/.*/podcast/.*/id(\d+)", re.IGNORECASE)
YOUTUBE_CHANNEL_PATTERN = re.compile(
    r"(?:youtube\.com/(?:@|c/|channel/)|youtu\.be/)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ManualReviewLink:
    kind: str  # social | content_channel
    channel_type: str | None
    url: str
    label: str = ""


def _strip_tracking_query(url: str) -> str:
    parsed = urlparse(url.strip())
    return normalize_url(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")


def parse_manual_review_link(url: str) -> ManualReviewLink | None:
    cleaned = _strip_tracking_query(url)
    lowered = cleaned.lower()

    if SPOTIFY_SHOW_PATTERN.search(lowered):
        return ManualReviewLink(kind="content_channel", channel_type="spotify_show", url=cleaned)

    if APPLE_PODCAST_PATTERN.search(lowered) and "/podcast/" in lowered:
        return ManualReviewLink(kind="content_channel", channel_type="apple_podcast", url=cleaned)

    if YOUTUBE_CHANNEL_PATTERN.search(lowered) and "/watch" not in lowered and "/shorts/" not in lowered:
        canonical = canonicalize_profile_url(cleaned)
        if canonical is None:
            return ManualReviewLink(kind="content_channel", channel_type="youtube_channel", url=cleaned)
        return ManualReviewLink(kind="content_channel", channel_type="youtube_channel", url=canonical)

    canonical = canonicalize_profile_url(cleaned)
    if canonical is not None:
        return ManualReviewLink(kind="social", channel_type=None, url=canonical)

    platform = classify_platform(cleaned)
    if platform:
        return ManualReviewLink(kind="social", channel_type=None, url=cleaned)

    return None


def register_manual_content_channel(
    persona_id: str,
    link: ManualReviewLink,
    *,
    label: str = "",
    root=None,
) -> str:
    rss_url = None
    apple_podcast_id = None
    if link.channel_type == "spotify_show":
        rss_url, apple_podcast_id = resolve_spotify_show_rss(link.url, search_term=label or None)
    elif link.channel_type == "apple_podcast":
        rss_url, apple_podcast_id = resolve_apple_podcast_rss(link.url)
    elif link.channel_type == "podcast_rss":
        rss_url = link.url

    channel = add_channel(
        persona_id,
        channel_type=link.channel_type or "podcast_rss",
        url=link.url,
        label=label or link.url,
        rss_url=rss_url,
        apple_podcast_id=apple_podcast_id,
        root=root,
    )
    return channel.channel_id
