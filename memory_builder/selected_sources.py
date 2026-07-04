from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_builder.channel_registry import (
    CHANNEL_TYPE_PRIORITY,
    add_channel,
    archive_channel,
    channel_id_from_url,
    get_channel,
    load_channels,
)
from memory_builder.discovery.profile_urls import canonicalize_profile_url, classify_platform
from memory_builder.review.manual_link import parse_manual_review_link, register_manual_content_channel
from memory_builder.source_registry import (
    ApprovedSources,
    SourceCandidate,
    load_approved,
    save_approved,
    username_from_url,
)
from memory_builder.storage.sqlite_store import normalize_url


CONTENT_CHANNEL_TYPES = frozenset(
    {"youtube_channel", "spotify_show", "apple_podcast", "podcast_rss", "web_site"}
)

CHANNEL_TYPE_TO_PLATFORM: dict[str, str] = {
    "youtube_channel": "youtube",
    "spotify_show": "spotify",
    "apple_podcast": "podcast",
    "podcast_rss": "podcast",
    "web_site": "web",
    "x_profile": "x",
    "instagram_profile": "instagram",
    "facebook_profile": "facebook",
    "tiktok_profile": "tiktok",
    "threads_profile": "threads",
    "linkedin_profile": "linkedin",
}

PLATFORM_TO_CHANNEL_TYPE: dict[str, str] = {
    "youtube": "youtube_channel",
    "spotify": "spotify_show",
    "podcast": "podcast_rss",
    "apple_podcast": "apple_podcast",
    "web": "web_site",
    "x": "x_profile",
    "twitter": "x_profile",
    "instagram": "instagram_profile",
    "facebook": "facebook_profile",
    "tiktok": "tiktok_profile",
    "threads": "threads_profile",
    "linkedin": "linkedin_profile",
}


@dataclass
class SelectedSource:
    channel_id: str
    type: str
    url: str
    label: str
    platform: str
    priority: int
    confidence: float
    discovery_source: str
    username: str
    rss_url: str | None
    latest_published_at: str | None
    last_discovered_at: str | None
    added_at: str
    archived: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "type": self.type,
            "url": self.url,
            "label": self.label,
            "platform": self.platform,
            "priority": self.priority,
            "confidence": self.confidence,
            "discovery_source": self.discovery_source,
            "username": self.username,
            "rss_url": self.rss_url,
            "latest_published_at": self.latest_published_at,
            "last_discovered_at": self.last_discovered_at,
            "added_at": self.added_at,
            "archived": self.archived,
        }


def _normalize_source_url(url: str) -> str:
    canonical = canonicalize_profile_url(url)
    if canonical is not None:
        return canonical
    return normalize_url(url)


def _urls_match(left: str, right: str) -> bool:
    return _normalize_source_url(left) == _normalize_source_url(right)


def channel_type_for_platform(platform: str) -> str:
    normalized = platform.lower()
    if normalized == "twitter":
        normalized = "x"
    return PLATFORM_TO_CHANNEL_TYPE.get(normalized, f"{normalized}_profile")


def platform_for_channel_type(channel_type: str) -> str:
    return CHANNEL_TYPE_TO_PLATFORM.get(channel_type, channel_type.removesuffix("_profile"))


def _source_label(source: SourceCandidate) -> str:
    if source.label:
        return source.label
    username = source.username or username_from_url(source.url)
    if username:
        return f"@{username}"
    return source.url


def _channel_id_for_source(source: SourceCandidate) -> str:
    channel_type = channel_type_for_platform(source.platform)
    return channel_id_from_url(channel_type, source.url)


def _registry_channel_for_source(source: SourceCandidate, registry) -> Any | None:
    channel_id = _channel_id_for_source(source)
    channel = get_channel(registry, channel_id)
    if channel is not None:
        return channel
    for item in registry.channels:
        if _urls_match(item.url, source.url):
            return item
    return None


def _selected_from_source(source: SourceCandidate, registry) -> SelectedSource:
    channel_type = channel_type_for_platform(source.platform)
    registry_channel = _registry_channel_for_source(source, registry)
    channel_id = registry_channel.channel_id if registry_channel else _channel_id_for_source(source)
    if registry_channel:
        channel_type = registry_channel.type
    return SelectedSource(
        channel_id=channel_id,
        type=channel_type,
        url=source.url,
        label=registry_channel.label if registry_channel and registry_channel.label else _source_label(source),
        platform=source.platform,
        priority=CHANNEL_TYPE_PRIORITY.get(channel_type, 100),
        confidence=source.confidence,
        discovery_source=source.discovery_source,
        username=source.username or username_from_url(source.url),
        rss_url=registry_channel.rss_url if registry_channel else None,
        latest_published_at=registry_channel.latest_published_at if registry_channel else None,
        last_discovered_at=registry_channel.last_discovered_at if registry_channel else None,
        added_at=registry_channel.added_at if registry_channel and registry_channel.added_at else "",
        archived=bool(source.archived),
    )


def _bootstrap_missing_from_registry(persona_id: str, root: Path | None = None) -> None:
    approved = load_approved(persona_id, root)
    if approved is None:
        return
    registry = load_channels(persona_id, root)
    changed = False
    for channel in registry.channels:
        if channel.type not in {"youtube_channel", "spotify_show", "apple_podcast"}:
            continue
        if any(_urls_match(source.url, channel.url) for source in approved.sources):
            continue
        platform = platform_for_channel_type(channel.type)
        candidate = SourceCandidate(
            url=channel.url,
            platform=platform,
            confidence=1.0,
            discovery_source="channel_registry",
            username=username_from_url(channel.url),
            signals=["channel_registry"],
            status="approved",
            label=channel.label,
            archived=bool(channel.metadata.get("archived")),
        )
        _upsert_approved_source(approved, candidate)
        changed = True
    if changed:
        save_approved(approved, root)


def list_selected_sources(persona_id: str, root: Path | None = None) -> list[SelectedSource]:
    _bootstrap_missing_from_registry(persona_id, root)
    approved = load_approved(persona_id, root)
    if approved is None:
        return []
    registry = load_channels(persona_id, root)
    items = [_selected_from_source(source, registry) for source in approved.sources]
    items.sort(key=lambda item: (item.archived, item.priority, item.url))
    return items


def _ensure_approved(persona_id: str, root: Path | None = None) -> ApprovedSources:
    approved = load_approved(persona_id, root)
    if approved is not None:
        return approved
    return ApprovedSources(
        persona_id=persona_id,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        reviewed_by="dashboard",
        sources=[],
    )


def _upsert_approved_source(approved: ApprovedSources, candidate: SourceCandidate) -> SourceCandidate:
    for index, existing in enumerate(approved.sources):
        if _urls_match(existing.url, candidate.url):
            merged = SourceCandidate(
                url=candidate.url,
                platform=candidate.platform,
                confidence=max(existing.confidence, candidate.confidence),
                discovery_source=candidate.discovery_source or existing.discovery_source,
                username=candidate.username or existing.username,
                signals=list(dict.fromkeys([*existing.signals, *candidate.signals])),
                status="approved",
                label=candidate.label or existing.label,
                archived=existing.archived,
            )
            approved.sources[index] = merged
            return merged
    approved.sources.append(candidate)
    return candidate


def sync_approved_content_channels(persona_id: str, root: Path | None = None) -> None:
    approved = load_approved(persona_id, root)
    if approved is None:
        return
    for source in approved.sources:
        if source.archived:
            continue
        channel_type = channel_type_for_platform(source.platform)
        if channel_type not in CONTENT_CHANNEL_TYPES:
            continue
        register_manual_content_channel(
            persona_id,
            parse_manual_review_link(source.url) or _fallback_manual_link(source, channel_type),
            label=_source_label(source),
            root=root,
        )


def _fallback_manual_link(source: SourceCandidate, channel_type: str):
    from memory_builder.review.manual_link import ManualReviewLink

    return ManualReviewLink(kind="content_channel", channel_type=channel_type, url=source.url, label=_source_label(source))


def add_selected_source(
    persona_id: str,
    *,
    channel_type: str,
    url: str,
    label: str = "",
    rss_url: str | None = None,
    root: Path | None = None,
) -> SelectedSource:
    parsed = parse_manual_review_link(url)
    if parsed is not None and parsed.kind == "content_channel":
        channel_type = parsed.channel_type or channel_type
        url = parsed.url

    platform = platform_for_channel_type(channel_type)
    canonical = canonicalize_profile_url(url)
    normalized_url = canonical or normalize_url(url)
    if canonical is None and classify_platform(normalized_url):
        platform = classify_platform(normalized_url) or platform

    candidate = SourceCandidate(
        url=normalized_url,
        platform=platform,
        confidence=1.0,
        discovery_source="manual",
        username=username_from_url(normalized_url),
        signals=["user_submitted"],
        status="approved",
        label=label,
    )
    approved = _ensure_approved(persona_id, root)
    approved.reviewed_at = datetime.now(timezone.utc).isoformat()
    approved.reviewed_by = "dashboard"
    saved = _upsert_approved_source(approved, candidate)
    save_approved(approved, root)

    if channel_type in CONTENT_CHANNEL_TYPES:
        add_channel(
            persona_id,
            channel_type=channel_type,
            url=normalized_url,
            label=label or _source_label(saved),
            rss_url=rss_url,
            root=root,
        )
    elif parsed is not None and parsed.kind == "content_channel":
        register_manual_content_channel(persona_id, parsed, label=label or _source_label(saved), root=root)

    registry = load_channels(persona_id, root)
    return _selected_from_source(saved, registry)


def archive_selected_source(
    persona_id: str,
    channel_id: str,
    *,
    archived: bool = True,
    root: Path | None = None,
) -> SelectedSource:
    approved = load_approved(persona_id, root)
    if approved is None:
        raise ValueError(f"No approved sources for {persona_id}")

    registry = load_channels(persona_id, root)
    target: SourceCandidate | None = None
    for source in approved.sources:
        if _channel_id_for_source(source) == channel_id:
            target = source
            break
        registry_channel = _registry_channel_for_source(source, registry)
        if registry_channel and registry_channel.channel_id == channel_id:
            target = source
            break
    if target is None:
        raise ValueError(f"Unknown selected source: {channel_id}")

    target.archived = archived
    save_approved(approved, root)

    registry_channel = _registry_channel_for_source(target, registry)
    if registry_channel is not None:
        archive_channel(persona_id, registry_channel.channel_id, archived=archived, root=root)
        registry = load_channels(persona_id, root)

    return _selected_from_source(target, registry)


def update_selected_label(
    persona_id: str,
    channel_id: str,
    *,
    label: str,
    root: Path | None = None,
) -> SelectedSource:
    approved = load_approved(persona_id, root)
    if approved is None:
        raise ValueError(f"No approved sources for {persona_id}")
    registry = load_channels(persona_id, root)
    target: SourceCandidate | None = None
    for source in approved.sources:
        if _channel_id_for_source(source) == channel_id:
            target = source
            break
        registry_channel = _registry_channel_for_source(source, registry)
        if registry_channel and registry_channel.channel_id == channel_id:
            target = source
            break
    if target is None:
        raise ValueError(f"Unknown selected source: {channel_id}")

    target.label = label
    save_approved(approved, root)

    registry_channel = _registry_channel_for_source(target, registry)
    if registry_channel is not None:
        registry_channel.label = label
        from memory_builder.channel_registry import save_channels

        save_channels(registry, root)
        registry = load_channels(persona_id, root)

    return _selected_from_source(target, registry)
