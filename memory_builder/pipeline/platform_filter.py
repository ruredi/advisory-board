from __future__ import annotations

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
