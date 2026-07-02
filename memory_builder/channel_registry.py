from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from memory_builder.config import load_persona_config
from memory_builder.paths import project_root


CHANNEL_TYPE_PRIORITY = {
    "youtube_channel": 10,
    "podcast_rss": 20,
    "apple_podcast": 20,
    "spotify_show": 25,
}


@dataclass
class ContentChannel:
    channel_id: str
    type: str
    url: str
    label: str = ""
    priority: int = 100
    rss_url: str | None = None
    apple_podcast_id: str | None = None
    latest_published_at: str | None = None
    last_discovered_at: str | None = None
    added_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("metadata"):
            data.pop("metadata", None)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentChannel:
        return cls(
            channel_id=data["channel_id"],
            type=data["type"],
            url=data["url"],
            label=data.get("label", ""),
            priority=int(data.get("priority", CHANNEL_TYPE_PRIORITY.get(data.get("type", ""), 100))),
            rss_url=data.get("rss_url"),
            apple_podcast_id=data.get("apple_podcast_id"),
            latest_published_at=data.get("latest_published_at"),
            last_discovered_at=data.get("last_discovered_at"),
            added_at=data.get("added_at", ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ChannelRegistry:
    persona_id: str
    channels: list[ContentChannel]

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "channels": [channel.to_dict() for channel in self.channels],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelRegistry:
        return cls(
            persona_id=data["persona_id"],
            channels=[ContentChannel.from_dict(item) for item in data.get("channels", [])],
        )


def channels_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "sources" / "channels"
    path.mkdir(parents=True, exist_ok=True)
    return path


def channels_path(persona_id: str, root: Path | None = None) -> Path:
    return channels_dir(root) / f"{persona_id}.yaml"


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in value.lower())
    return "-".join(part for part in cleaned.split("-") if part)[:80]


def channel_id_from_url(channel_type: str, url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "-")
    host = parsed.netloc.lower().removeprefix("www.")
    base = path or host
    return _slugify(f"{channel_type}-{base}")


def _watch_feed_to_channel(feed: dict[str, str]) -> ContentChannel | None:
    feed_type = feed.get("type", "")
    url = feed.get("url", "").strip()
    if not url:
        return None
    if feed_type not in {"youtube_channel", "rss", "web"}:
        return None
    channel_type = "youtube_channel" if feed_type == "youtube_channel" else "podcast_rss"
    label = feed.get("label", url)
    channel_id = channel_id_from_url(channel_type, url)
    return ContentChannel(
        channel_id=channel_id,
        type=channel_type,
        url=url,
        label=label,
        priority=CHANNEL_TYPE_PRIORITY.get(channel_type, 100),
        rss_url=url if feed_type == "rss" else None,
        added_at=datetime.now(timezone.utc).isoformat(),
    )


def bootstrap_channels_from_config(persona_id: str, root: Path | None = None) -> ChannelRegistry:
    config = load_persona_config(persona_id, root)
    channels: list[ContentChannel] = []
    seen_ids: set[str] = set()
    for feed in config.watch_feeds:
        channel = _watch_feed_to_channel(feed)
        if channel is None or channel.channel_id in seen_ids:
            continue
        seen_ids.add(channel.channel_id)
        channels.append(channel)
    channels.sort(key=lambda item: (item.priority, item.url))
    return ChannelRegistry(persona_id=persona_id, channels=channels)


def load_channels(persona_id: str, root: Path | None = None) -> ChannelRegistry:
    path = channels_path(persona_id, root)
    if not path.exists():
        registry = bootstrap_channels_from_config(persona_id, root)
        if registry.channels:
            save_channels(registry, root)
        return registry
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return ChannelRegistry(persona_id=persona_id, channels=[])
    return ChannelRegistry.from_dict(data)


def save_channels(registry: ChannelRegistry, root: Path | None = None) -> Path:
    path = channels_path(registry.persona_id, root)
    path.write_text(
        yaml.safe_dump(registry.to_dict(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def get_channel(registry: ChannelRegistry, channel_id: str) -> ContentChannel | None:
    for channel in registry.channels:
        if channel.channel_id == channel_id:
            return channel
    return None


def add_channel(
    persona_id: str,
    *,
    channel_type: str,
    url: str,
    label: str = "",
    rss_url: str | None = None,
    apple_podcast_id: str | None = None,
    root: Path | None = None,
) -> ContentChannel:
    registry = load_channels(persona_id, root)
    channel_id = channel_id_from_url(channel_type, url)
    existing = get_channel(registry, channel_id)
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        existing.url = url
        existing.label = label or existing.label
        existing.rss_url = rss_url or existing.rss_url
        existing.apple_podcast_id = apple_podcast_id or existing.apple_podcast_id
        save_channels(registry, root)
        return existing

    channel = ContentChannel(
        channel_id=channel_id,
        type=channel_type,
        url=url,
        label=label or url,
        priority=CHANNEL_TYPE_PRIORITY.get(channel_type, 100),
        rss_url=rss_url,
        apple_podcast_id=apple_podcast_id,
        added_at=now,
    )
    registry.channels.append(channel)
    registry.channels.sort(key=lambda item: (item.priority, item.url))
    save_channels(registry, root)
    return channel


def update_channel_cursor(
    persona_id: str,
    channel_id: str,
    *,
    latest_published_at: str | None = None,
    last_discovered_at: str | None = None,
    root: Path | None = None,
) -> None:
    registry = load_channels(persona_id, root)
    channel = get_channel(registry, channel_id)
    if channel is None:
        return
    if latest_published_at:
        channel.latest_published_at = latest_published_at
    if last_discovered_at:
        channel.last_discovered_at = last_discovered_at
    save_channels(registry, root)


def sorted_channels(registry: ChannelRegistry, *, include_archived: bool = False) -> list[ContentChannel]:
    channels = registry.channels
    if not include_archived:
        channels = [channel for channel in channels if not channel.metadata.get("archived")]
    return sorted(channels, key=lambda item: (item.priority, item.url))


def is_channel_archived(channel: ContentChannel) -> bool:
    return bool(channel.metadata.get("archived"))


def archive_channel(
    persona_id: str,
    channel_id: str,
    *,
    archived: bool = True,
    root: Path | None = None,
) -> ContentChannel:
    registry = load_channels(persona_id, root)
    channel = get_channel(registry, channel_id)
    if channel is None:
        raise ValueError(f"Unknown channel: {channel_id}")
    channel.metadata["archived"] = archived
    save_channels(registry, root)
    return channel
