from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory_builder.channel_registry import ContentChannel

PLATFORM_ALIASES: dict[str, str] = {
    "twitter": "x",
}

SUPPORTED_PLATFORMS: frozenset[str] = frozenset({"youtube", "spotify", "x", "instagram", "web"})


def normalize_platform_filter(platform: str) -> str:
    key = platform.strip().lower()
    normalized = PLATFORM_ALIASES.get(key, key)
    if normalized not in SUPPORTED_PLATFORMS:
        supported = ", ".join(sorted(SUPPORTED_PLATFORMS))
        raise ValueError(f"Unsupported --only platform {platform!r}. Choose from: {supported}")
    return normalized


def social_profile_matches_filter(profile_platform: str, only_platform: str | None) -> bool:
    if only_platform is None:
        return True
    normalized_only = normalize_platform_filter(only_platform)
    profile_key = profile_platform.strip().lower()
    profile_normalized = PLATFORM_ALIASES.get(profile_key, profile_key)
    return profile_normalized == normalized_only


def channel_matches_platform(channel: "ContentChannel", only_platform: str | None) -> bool:
    if only_platform is None:
        return True
    normalized = normalize_platform_filter(only_platform)
    if normalized in {"instagram", "x", "web"}:
        return False
    if channel.type == "youtube_channel":
        return normalized == "youtube"
    if channel.type in {"spotify_show", "apple_podcast"}:
        return normalized == "spotify"
    if channel.type == "podcast_rss":
        combined = f"{channel.url} {channel.rss_url or ''}".lower()
        if "youtube.com" in combined or "youtu.be" in combined:
            return normalized == "youtube"
        return normalized == "spotify"
    return False


def source_url_matches_platform(source_url: str, source_type: str, only_platform: str | None) -> bool:
    if only_platform is None:
        return True
    normalized = normalize_platform_filter(only_platform)
    lowered = source_url.lower()
    if normalized == "youtube":
        return source_type == "youtube" or "youtube.com" in lowered or "youtu.be" in lowered
    if normalized == "spotify":
        return source_type == "podcast" and any(
            token in lowered for token in ("spotify.com", "flightcast.com", "podcasts.apple.com")
        )
    if normalized == "x":
        return source_type == "social" and any(token in lowered for token in ("x.com/", "twitter.com/"))
    if normalized == "instagram":
        return source_type == "social" and "instagram.com" in lowered
    if normalized == "web":
        return source_type in {"web", "pdf"}
    return True


def platform_sql_filter(platform: str | None) -> tuple[str, list[object]]:
    if platform is None:
        return "", []
    normalized = normalize_platform_filter(platform)
    if normalized == "youtube":
        return " AND source_type = ?", ["youtube"]
    if normalized == "spotify":
        return (
            """
            AND source_type = ?
            AND (
                LOWER(source_url) LIKE '%flightcast.com%'
                OR LOWER(source_url) LIKE '%spotify.com%'
                OR LOWER(COALESCE(channel_url, '')) LIKE '%spotify.com%'
            )
            """,
            ["podcast"],
        )
    if normalized == "x":
        return (
            """
            AND source_type = ?
            AND (
                LOWER(source_url) LIKE '%x.com/%'
                OR LOWER(source_url) LIKE '%twitter.com/%'
            )
            """,
            ["social"],
        )
    if normalized == "instagram":
        return (
            " AND source_type = ? AND LOWER(source_url) LIKE '%instagram.com%'",
            ["social"],
        )
    if normalized == "web":
        return " AND source_type = ?", ["web"]
    raise ValueError(f"Unsupported platform filter: {platform}")
