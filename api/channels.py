from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.deps import ensure_persona
from api.schemas import ChannelCreateRequest, ChannelItem, ChannelPatchRequest
from memory_builder.selected_sources import (
    add_selected_source,
    archive_selected_source,
    list_selected_sources,
    update_selected_label,
)

router = APIRouter(tags=["channels"])


def _channel_item(source) -> ChannelItem:
    return ChannelItem(
        channel_id=source.channel_id,
        type=source.type,
        url=source.url,
        label=source.label,
        priority=source.priority,
        rss_url=source.rss_url,
        latest_published_at=source.latest_published_at,
        last_discovered_at=source.last_discovered_at,
        added_at=source.added_at,
        archived=source.archived,
    )


@router.get("/personas/{persona_id}/channels", response_model=list[ChannelItem])
def list_channels(persona_id: str, include_archived: bool = True) -> list[ChannelItem]:
    ensure_persona(persona_id)
    sources = list_selected_sources(persona_id)
    if not include_archived:
        sources = [source for source in sources if not source.archived]
    return [_channel_item(source) for source in sources]


@router.post("/personas/{persona_id}/channels", response_model=ChannelItem)
def create_channel(persona_id: str, body: ChannelCreateRequest) -> ChannelItem:
    ensure_persona(persona_id)
    source = add_selected_source(
        persona_id,
        channel_type=body.channel_type,
        url=body.url,
        label=body.label,
        rss_url=body.rss_url,
    )
    return _channel_item(source)


@router.patch("/personas/{persona_id}/channels/{channel_id}", response_model=ChannelItem)
def patch_channel(persona_id: str, channel_id: str, body: ChannelPatchRequest) -> ChannelItem:
    ensure_persona(persona_id)
    try:
        if body.label is not None:
            source = update_selected_label(persona_id, channel_id, label=body.label)
        elif body.archived is not None:
            source = archive_selected_source(persona_id, channel_id, archived=body.archived)
        else:
            raise HTTPException(status_code=400, detail="No changes requested")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _channel_item(source)
