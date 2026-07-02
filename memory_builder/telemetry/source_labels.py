from __future__ import annotations

from typing import Any

from urllib.parse import urlparse

from memory_builder.models import SourceType


TYPE_LABELS: dict[str, str] = {
    SourceType.YOUTUBE: "YouTube",
    SourceType.PODCAST: "Podcast",
    SourceType.WEB: "Web",
    SourceType.PDF: "PDF",
    SourceType.SOCIAL: "Social",
    SourceType.IMAGE: "Image",
    SourceType.UNKNOWN: "Unknown",
}

STAGE_LABELS: dict[str, str] = {
    "discovery": "discovery",
    "source_start": "queued",
    "source_fetch": "fetching",
    "source_extract": "extracting",
    "source_index": "indexing",
    "source_done": "done",
    "source_error": "error",
    "source_skip": "skipped",
    "run_started": "started",
    "run_finished": "finished",
}


def platform_label(source_type: str, source_url: str = "", channel_url: str = "") -> str:
    combined = f"{source_url} {channel_url}".lower()
    lowered = source_url.lower()

    if source_type == SourceType.SOCIAL or any(
        host in lowered for host in ("x.com", "twitter.com", "instagram.com", "facebook.com", "linkedin.com")
    ):
        if "x.com" in lowered or "twitter.com" in lowered:
            return "X"
        if "instagram.com" in lowered:
            return "Instagram"
        if "facebook.com" in lowered:
            return "Facebook"
        if "linkedin.com" in lowered:
            return "LinkedIn"
        return "Social"

    if "youtube.com" in combined or "youtu.be" in combined:
        return "YouTube"

    if source_type == SourceType.PODCAST or any(
        token in combined for token in ("flightcast.com", "spotify.com", ".mp3", ".m4a")
    ):
        if "podcasts.apple.com" in combined:
            return "Apple Podcasts"
        if "spotify.com" in combined or "flightcast.com" in combined:
            return "Spotify"
        return "Podcast"

    return TYPE_LABELS.get(source_type, source_type.title() if source_type else "Unknown")


def short_url(source_url: str, *, max_len: int = 60) -> str:
    if not source_url:
        return ""
    if source_url.startswith("podcast-entry:"):
        return source_url.removeprefix("podcast-entry:")[:max_len]
    parsed = urlparse(source_url)
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path.rstrip("/")
    compact = f"{host}{path}" if host else source_url
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def stage_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage.replace("_", " "))


def extract_stage_label(stage: str, metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    if stage == "source_extract":
        chunk_index = meta.get("chunk_index")
        chunk_total = meta.get("chunk_total")
        if chunk_index and chunk_total:
            return f"extracting chunk {chunk_index}/{chunk_total}"
    return stage_label(stage)
