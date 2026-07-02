from __future__ import annotations

from urllib.parse import urlunparse, urlparse

from memory_builder.storage.sqlite_store import normalize_url


SOCIAL_HOST_PATTERNS: list[tuple[str, str]] = [
    ("x.com", "x"),
    ("twitter.com", "x"),
    ("instagram.com", "instagram"),
    ("linkedin.com", "linkedin"),
    ("facebook.com", "facebook"),
    ("tiktok.com", "tiktok"),
    ("threads.net", "threads"),
    ("youtube.com", "youtube"),
]

YOUTUBE_PROFILE_SUBPAGES = frozenset(
    {
        "videos",
        "streams",
        "shorts",
        "playlists",
        "community",
        "about",
        "featured",
        "channels",
        "posts",
        "releases",
        "store",
        "live",
        "podcasts",
    }
)

X_RESERVED = frozenset({"home", "search", "explore", "i", "intent", "settings"})
INSTAGRAM_RESERVED = frozenset({"p", "reel", "reels", "stories", "explore", "tv", "accounts"})


def classify_platform(url: str) -> str | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for needle, platform in SOCIAL_HOST_PATTERNS:
        if host == needle or host.endswith("." + needle):
            return platform
    return None


def _strip_youtube_subpages(parts: list[str]) -> list[str]:
    trimmed = list(parts)
    while len(trimmed) >= 2 and trimmed[-1].lower() in YOUTUBE_PROFILE_SUBPAGES:
        trimmed.pop()
    return trimmed


def _canonical_youtube_profile(parts: list[str]) -> str | None:
    parts = _strip_youtube_subpages(parts)
    if not parts or parts[0].lower() in YOUTUBE_PROFILE_SUBPAGES:
        return None

    if len(parts) == 1 and parts[0].startswith("@"):
        return f"https://youtube.com/@{parts[0][1:]}"

    if len(parts) == 2 and parts[0].lower() == "c":
        return f"https://youtube.com/@{parts[1]}"

    if len(parts) == 2 and parts[0].lower() == "user":
        return f"https://youtube.com/@{parts[1]}"

    if len(parts) == 2 and parts[0].lower() == "channel":
        return f"https://youtube.com/channel/{parts[1]}"

    return None


def canonicalize_profile_url(url: str) -> str | None:
    """Normalize a social profile URL to its homepage form, or None if not a profile."""
    normalized = normalize_url(url.strip())
    platform = classify_platform(normalized)
    if not platform:
        return None

    parsed = urlparse(normalized)
    host = parsed.netloc.lower().removeprefix("www.")
    if platform == "x" and host == "twitter.com":
        parsed = parsed._replace(netloc="x.com")

    parts = [part for part in parsed.path.strip("/").split("/") if part]

    if platform == "youtube":
        canonical = _canonical_youtube_profile(parts)
        return canonical

    if platform == "x":
        if len(parts) != 1 or parts[0].lower() in X_RESERVED:
            return None
        return "https://x.com/" + parts[0].lower()

    if platform == "instagram":
        if len(parts) != 1 or parts[0].lower() in INSTAGRAM_RESERVED:
            return None
        return f"https://instagram.com/{parts[0].lower()}"

    if platform == "linkedin":
        if len(parts) != 2 or parts[0].lower() != "in":
            return None
        return f"https://linkedin.com/in/{parts[1].lower()}"

    if platform == "tiktok":
        if len(parts) != 1 or not parts[0].startswith("@"):
            return None
        return f"https://tiktok.com/@{parts[0][1:].lower()}"

    if platform == "facebook":
        from memory_builder.fetch.scrapfly_facebook import parse_facebook_target

        target = parse_facebook_target(normalized)
        if target is None or target.kind not in {"page", "group", "profile"}:
            return None
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))

    if platform == "threads":
        if len(parts) != 1:
            return None
        handle = parts[0].lstrip("@").lower()
        return f"https://threads.net/@{handle}"

    return None


def profile_identity_key(url: str) -> str | None:
    """Stable dedup key for the same account across URL variants."""
    canonical = canonicalize_profile_url(url)
    if canonical is None:
        return None

    platform = classify_platform(canonical)
    parts = [part for part in urlparse(canonical).path.strip("/").split("/") if part]

    if platform == "youtube":
        if parts and parts[0].startswith("@"):
            return f"youtube:@{parts[0][1:].lower()}"
        if len(parts) == 2 and parts[0].lower() == "channel":
            return f"youtube:channel:{parts[1]}"
        return None

    if platform == "x":
        return f"x:{parts[0].lower()}"

    if platform == "instagram":
        return f"instagram:{parts[0].lower()}"

    if platform == "linkedin":
        return f"linkedin:in:{parts[1].lower()}"

    if platform == "tiktok":
        return f"tiktok:@{parts[0][1:].lower()}"

    if platform == "threads":
        return f"threads:@{parts[0].lstrip('@').lower()}"

    if platform == "facebook":
        return f"facebook:{canonical.lower()}"

    return None
