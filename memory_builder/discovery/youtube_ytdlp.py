from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

from memory_builder.discovery.seed_links import classify_source_type, infer_source_nature
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import normalize_url


log = logging.getLogger(__name__)

YTDLP_PRINT_FORMAT = "%(webpage_url)s\t%(title)s\t%(upload_date)s"


def ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _youtube_videos_tab_url(channel_url: str) -> str:
    url = channel_url.strip().rstrip("/")
    if url.endswith("/videos") or url.endswith("/shorts") or url.endswith("/streams"):
        return url
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if "@" in path or path.startswith("/c/") or path.startswith("/channel/") or path.startswith("/user/"):
        return f"{url}/videos"
    return url


def resolve_youtube_channel_id_ytdlp(channel_url: str) -> str | None:
    if not ytdlp_available():
        return None
    cmd = [
        "yt-dlp",
        "--playlist-items",
        "1",
        "--no-warnings",
        "--no-update",
        "--print",
        "%(channel_id)s",
        _youtube_videos_tab_url(channel_url),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("yt-dlp channel id lookup failed for %s: %s", channel_url, exc)
        return None
    channel_id = (result.stdout or "").strip().splitlines()[0] if result.stdout else ""
    if channel_id.startswith("UC") and len(channel_id) >= 20:
        return channel_id
    return None


def _upload_date_iso(raw: str) -> str | None:
    value = raw.strip()
    if not value or value == "NA" or len(value) != 8:
        return None
    try:
        year = int(value[0:4])
        month = int(value[4:6])
        day = int(value[6:8])
        return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def discover_youtube_channel_ytdlp(
    persona_id: str,
    channel_url: str,
    seen: set[str],
    *,
    watermark: str | None = None,
    channel_url_meta: str | None = None,
) -> list[SourceRecord]:
    if not ytdlp_available():
        log.warning("yt-dlp not found — cannot discover YouTube channel %s", channel_url)
        return []

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--no-update",
        "--print",
        YTDLP_PRINT_FORMAT,
        _youtube_videos_tab_url(channel_url),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("yt-dlp channel discovery failed for %s: %s", channel_url, exc)
        return []

    if result.returncode not in {0, 1}:
        log.warning(
            "yt-dlp exited %s for %s: %s",
            result.returncode,
            channel_url,
            (result.stderr or "").strip()[:200],
        )

    records: list[SourceRecord] = []
    meta_url = channel_url_meta or channel_url
    for line in (result.stdout or "").splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 2:
            continue
        link = normalize_url(parts[0].strip())
        title = parts[1].strip() or link
        published = _upload_date_iso(parts[2]) if len(parts) > 2 else None
        if not link or link in seen:
            continue
        if classify_source_type(link) != SourceType.YOUTUBE:
            continue
        if watermark and published and published <= watermark:
            continue
        seen.add(link)
        records.append(
            SourceRecord(
                persona_id=persona_id,
                source_url=link,
                source_title=title,
                source_type=SourceType.YOUTUBE,
                source_date=published,
                source_nature=infer_source_nature(SourceType.YOUTUBE, link),
                status=SourceStatus.PENDING,
                channel_url=meta_url,
            )
        )
    return records
