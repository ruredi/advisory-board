from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.deps import ensure_persona
from api.schemas import ChannelCreateRequest, ChannelItem, ChannelPatchRequest
from memory_builder.channel_registry import (
    add_channel,
    archive_channel,
    get_channel,
    is_channel_archived,
    load_channels,
    sorted_channels,
)

router = APIRouter(tags=["channels"])


def _channel_item(channel) -> ChannelItem:
    return ChannelItem(
        channel_id=channel.channel_id,
        type=channel.type,
        url=channel.url,
        label=channel.label,
        priority=channel.priority,
        rss_url=channel.rss_url,
        latest_published_at=channel.latest_published_at,
        last_discovered_at=channel.last_discovered_at,
        added_at=channel.added_at,
        archived=is_channel_archived(channel),
    )


@router.get("/personas/{persona_id}/channels", response_model=list[ChannelItem])
def list_channels(persona_id: str, include_archived: bool = True) -> list[ChannelItem]:
    ensure_persona(persona_id)
    registry = load_channels(persona_id)
    if include_archived:
        channels = sorted(registry.channels, key=lambda item: (item.priority, item.url))
    else:
        channels = sorted_channels(registry, include_archived=False)
    return [_channel_item(channel) for channel in channels]


@router.post("/personas/{persona_id}/channels", response_model=ChannelItem)
def create_channel(persona_id: str, body: ChannelCreateRequest) -> ChannelItem:
    ensure_persona(persona_id)
    channel = add_channel(
        persona_id,
        channel_type=body.channel_type,
        url=body.url,
        label=body.label,
        rss_url=body.rss_url,
    )
    return _channel_item(channel)


@router.patch("/personas/{persona_id}/channels/{channel_id}", response_model=ChannelItem)
def patch_channel(persona_id: str, channel_id: str, body: ChannelPatchRequest) -> ChannelItem:
    ensure_persona(persona_id)
    registry = load_channels(persona_id)
    channel = get_channel(registry, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    if body.label is not None:
        channel.label = body.label
        from memory_builder.channel_registry import save_channels

        save_channels(registry)
    if body.archived is not None:
        channel = archive_channel(persona_id, channel_id, archived=body.archived)
    else:
        channel = get_channel(load_channels(persona_id), channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return _channel_item(channel)
