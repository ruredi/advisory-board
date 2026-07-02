from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from memory_builder.config import load_persona_config
from memory_builder.discovery.profile_urls import (
    canonicalize_profile_url,
    classify_platform,
    profile_identity_key,
)
from memory_builder.discovery.seed_links import parse_seed_link_file
from memory_builder.source_registry import SourceCandidate, username_from_url
from memory_builder.storage.sqlite_store import normalize_url


AGGREGATOR_HOSTS = frozenset(
    {
        "threadreaderapp.com",
        "notcommon.com",
        "arrfounder.com",
    }
)

URL_IN_TEXT = re.compile(r"https?://[^\s<>\"'\\]+")


def _sanitize_discovered_url(url: str) -> str:
    return url.strip().rstrip("\\).,;'\"")


def _normalize_profile_url(url: str) -> str:
    canonical = canonicalize_profile_url(_sanitize_discovered_url(url))
    if canonical is None:
        return normalize_url(_sanitize_discovered_url(url))
    return canonical


def is_profile_candidate(url: str) -> bool:
    return canonicalize_profile_url(url) is not None


def score_candidate(url: str, discovery_source: str, allowed_domains: list[str]) -> tuple[float, list[str]]:
    platform = classify_platform(url) or "unknown"
    host = urlparse(url).netloc.lower().removeprefix("www.")
    signals: list[str] = [discovery_source]

    base_scores = {
        "official_site": 0.96,
        "seed_file": 0.90,
        "persona_config": 0.88,
        "watch_feed": 0.94,
        "manual": 1.0,
    }
    score = base_scores.get(discovery_source, 0.70)
    signals.append(f"platform:{platform}")

    if any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
        score = min(1.0, score + 0.02)
        signals.append("allowed_domain")

    if host in AGGREGATOR_HOSTS:
        score = min(score, 0.45)
        signals.append("aggregator")

    if platform == "facebook":
        signals.append("facebook_profile")

    return round(score, 2), signals


def _persona_name_tokens(display_name: str, speaker_names: list[str]) -> set[str]:
    tokens: set[str] = set()
    for name in [display_name, *speaker_names]:
        for part in re.split(r"[^a-z0-9]+", name.lower()):
            if len(part) >= 4:
                tokens.add(part)
    return tokens


def _matches_persona_identity(url: str, username: str, display_name: str, speaker_names: list[str]) -> bool:
    blob = f"{url} {username}".lower()
    return any(token in blob for token in _persona_name_tokens(display_name, speaker_names))


def _candidate_from_url(
    url: str,
    discovery_source: str,
    allowed_domains: list[str],
    *,
    display_name: str = "",
    speaker_names: list[str] | None = None,
) -> SourceCandidate | None:
    normalized = canonicalize_profile_url(_sanitize_discovered_url(url))
    if normalized is None:
        return None
    platform = classify_platform(normalized)
    if not platform:
        return None
    username = username_from_url(normalized)
    if discovery_source == "official_site" and display_name:
        if not _matches_persona_identity(normalized, username, display_name, speaker_names or []):
            return None
    confidence, signals = score_candidate(normalized, discovery_source, allowed_domains)
    return SourceCandidate(
        url=normalized,
        platform=platform,
        confidence=confidence,
        discovery_source=discovery_source,
        username=username,
        signals=signals,
    )


SOURCE_PRIORITY = {
    "manual": 6,
    "official_site": 5,
    "watch_feed": 4,
    "persona_config": 3,
    "seed_file": 2,
}


def _candidate_rank(candidate: SourceCandidate) -> tuple[float, int]:
    return (candidate.confidence, SOURCE_PRIORITY.get(candidate.discovery_source, 0))


def _merge_candidate(store: dict[str, SourceCandidate], candidate: SourceCandidate) -> None:
    key = profile_identity_key(candidate.url) or candidate.url.lower()
    existing = store.get(key)
    if existing is None:
        store[key] = candidate
        return
    if _candidate_rank(candidate) >= _candidate_rank(existing):
        candidate.signals = sorted(set(existing.signals + candidate.signals))
        store[key] = candidate


def discover_official_site_links(
    page_urls: list[str],
    allowed_domains: list[str],
    display_name: str,
    speaker_names: list[str],
) -> list[SourceCandidate]:
    found: dict[str, SourceCandidate] = {}
    for page_url in page_urls:
        try:
            response = httpx.get(page_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        for match in URL_IN_TEXT.findall(response.text):
            candidate = _candidate_from_url(
                match,
                "official_site",
                allowed_domains,
                display_name=display_name,
                speaker_names=speaker_names,
            )
            if candidate:
                _merge_candidate(found, candidate)
    return list(found.values())


def discover_persona_source_candidates(persona_id: str, root=None) -> list[SourceCandidate]:
    config = load_persona_config(persona_id, root)
    found: dict[str, SourceCandidate] = {}

    for seed_file in config.seed_link_files:
        for url in parse_seed_link_file(Path(seed_file)):
            candidate = _candidate_from_url(url, "seed_file", config.allowed_domains)
            if candidate:
                _merge_candidate(found, candidate)

    for profile in config.social_profiles:
        platform = str(profile.get("platform", "")).lower()
        username = str(profile.get("username", "")).strip().lstrip("@")
        profile_url = str(profile.get("url", "")).strip()
        if not profile_url and platform in {"x", "twitter"}:
            profile_url = f"https://x.com/{username}"
        elif not profile_url and platform == "instagram":
            profile_url = f"https://www.instagram.com/{username}/"
        if profile_url:
            candidate = _candidate_from_url(profile_url, "persona_config", config.allowed_domains)
            if candidate:
                _merge_candidate(found, candidate)

    for feed in config.watch_feeds:
        feed_url = feed.get("url", "")
        if not feed_url:
            continue
        feed_type = feed.get("type", "rss")
        if feed_type in {"youtube_channel", "rss", "web"}:
            candidate = _candidate_from_url(feed_url, "watch_feed", config.allowed_domains)
            if candidate:
                _merge_candidate(found, candidate)

    homepage_urls: list[str] = []
    for feed in config.watch_feeds:
        if feed.get("type") == "web" and feed.get("url"):
            homepage_urls.append(feed["url"])
    for seed_file in config.seed_link_files:
        for url in parse_seed_link_file(Path(seed_file)):
            if any(token in url.lower() for token in ("about", "bio", "/@")):
                homepage_urls.append(url)
    for domain in config.allowed_domains:
        homepage_urls.append(f"https://{domain}/")
    for candidate in discover_official_site_links(
        homepage_urls,
        config.allowed_domains,
        config.display_name,
        config.speaker_names,
    ):
        _merge_candidate(found, candidate)

    return sorted(found.values(), key=lambda item: (-item.confidence, item.url))
