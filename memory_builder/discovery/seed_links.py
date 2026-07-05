from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from memory_builder.fetch.scrapfly_facebook import is_facebook_post_url, is_facebook_profile_url
from memory_builder.models import MediaFormat, SourceNature, SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import normalize_url


URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def parse_seed_link_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = URL_PATTERN.search(line)
        if match:
            urls.append(normalize_url(match.group(0)))
    return urls


def is_social_post_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if any(token in host for token in ("x.com", "twitter.com")):
        return "/status/" in path
    if "instagram.com" in host:
        return "/p/" in path or "/reel/" in path
    if is_facebook_post_url(url):
        return True
    if "threadreaderapp.com" in host:
        return "/thread/" in path
    return False


def is_social_profile_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.strip("/")
    if not path:
        return False
    if any(token in host for token in ("x.com", "twitter.com")):
        parts = [part for part in path.split("/") if part]
        return len(parts) == 1 and parts[0].lower() not in {"home", "search", "explore", "i"}
    if "instagram.com" in host:
        parts = [part for part in path.split("/") if part]
        return len(parts) == 1 and parts[0].lower() not in {"p", "reel", "stories", "explore"}
    if is_facebook_profile_url(url):
        return True
    return False


def classify_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return SourceType.YOUTUBE
    if host.endswith(".pdf") or path.endswith(".pdf"):
        return SourceType.PDF
    if any(token in host for token in ("spotify.com", "podcasts.apple.com", "pocketcasts.com")):
        return SourceType.PODCAST
    if "threadreaderapp.com" in host and "/thread/" in path:
        return SourceType.WEB
    if any(token in host for token in ("x.com", "twitter.com", "instagram.com", "facebook.com", "linkedin.com")):
        return SourceType.SOCIAL
    return SourceType.WEB


def infer_source_nature(source_type: str, url: str) -> str:
    lowered = url.lower()
    if source_type in {SourceType.YOUTUBE, SourceType.PODCAST}:
        if any(token in lowered for token in ("keynote", "commencement", "speech")):
            return SourceNature.PERFORMED_SPOKEN
        return SourceNature.NATURAL_SPOKEN
    if source_type == SourceType.PDF:
        return SourceNature.WRITTEN
    if source_type == SourceType.WEB:
        return SourceNature.WRITTEN
    if source_type == SourceType.SOCIAL:
        return SourceNature.WRITTEN
    return SourceNature.UNCERTAIN


def infer_media_format(source_type: str, url: str) -> str:
    """Best-effort media format from URL only (before the post payload is fetched).

    Ambiguous social posts (Instagram /p/, X /status/) stay 'unknown' until
    processing determines the accurate format from the scraped payload.
    """
    lowered = url.lower()
    if source_type == SourceType.YOUTUBE:
        return MediaFormat.VIDEO
    if source_type == SourceType.PODCAST:
        return MediaFormat.AUDIO
    if source_type in {SourceType.PDF, SourceType.WEB}:
        return MediaFormat.TEXT
    if source_type == SourceType.SOCIAL:
        if any(token in lowered for token in ("/reel/", "/reels/", "/video/", "/videos/", "/watch/")):
            return MediaFormat.VIDEO
        return MediaFormat.UNKNOWN
    return MediaFormat.UNKNOWN


def is_processable_source(url: str, allowed_domains: list[str] | None = None) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    path = urlparse(url).path.rstrip("/")
    source_type = classify_source_type(url)

    if path in ("", "/"):
        return False

    profile_only_patterns = (
        "/about",
        "/bio",
        "/podcast",
        "/videos",
        "/user/",
        "threadreaderapp.com/user/",
        "notcommon.com/",
        "arrfounder.com/@",
    )
    for pattern in profile_only_patterns:
        if pattern in url and source_type != SourceType.YOUTUBE:
            return False
        if pattern in url and source_type == SourceType.YOUTUBE and not any(
            token in url for token in ("/watch", "/shorts/", "/live/")
        ):
            return False

    if source_type == SourceType.SOCIAL:
        if is_social_post_url(url):
            return True
        return False

    if source_type == SourceType.PODCAST:
        path_lower = urlparse(url).path.lower()
        if path_lower.endswith((".mp3", ".m4a", ".wav")):
            return True
        if url.startswith("podcast-entry:"):
            return True
        if "episode.flightcast.com" in host:
            return True

    if allowed_domains:
        allowed = any(host == domain or host.endswith("." + domain) for domain in allowed_domains)
        major_hosts = (
            "youtube.com",
            "youtu.be",
            "spotify.com",
            "podcasts.apple.com",
            "pocketcasts.com",
            "x.com",
            "twitter.com",
            "instagram.com",
            "facebook.com",
            "threadreaderapp.com",
        )
        on_major = any(host == item or host.endswith("." + item) for item in major_hosts)
        if not allowed and not on_major:
            return False

    return True


def discover_seed_sources(persona_id: str, seed_files: list[str]) -> list[SourceRecord]:
    discovered: list[SourceRecord] = []
    seen: set[str] = set()
    for file_path in seed_files:
        for url in parse_seed_link_file(Path(file_path)):
            if url in seen:
                continue
            seen.add(url)
            if not is_processable_source(url):
                continue
            source_type = classify_source_type(url)
            discovered.append(
                SourceRecord(
                    persona_id=persona_id,
                    source_url=url,
                    source_title=url,
                    source_type=source_type,
                    source_nature=infer_source_nature(source_type, url),
                    media_format=infer_media_format(source_type, url),
                    status=SourceStatus.PENDING,
                )
            )
    return discovered
