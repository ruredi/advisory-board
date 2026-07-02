from __future__ import annotations

import pytest

from memory_builder.channel_registry import (
    ContentChannel,
    ChannelRegistry,
    archive_channel,
    is_channel_archived,
    sorted_channels,
)


def test_archive_channel_filters_discovery(tmp_path, monkeypatch):
    channels_file = tmp_path / "sources" / "channels" / "hormozi.yaml"
    channels_file.parent.mkdir(parents=True)
    registry = ChannelRegistry(
        persona_id="hormozi",
        channels=[
            ContentChannel(
                channel_id="yt-test",
                type="youtube_channel",
                url="https://www.youtube.com/@test",
                label="Test",
            )
        ],
    )
    monkeypatch.setattr(
        "memory_builder.channel_registry.channels_path",
        lambda persona_id, root=None: channels_file,
    )
    from memory_builder.channel_registry import save_channels

    save_channels(registry, tmp_path)
    archived = archive_channel("hormozi", "yt-test", archived=True, root=tmp_path)
    assert is_channel_archived(archived)
    reloaded = sorted_channels(
        __import__("memory_builder.channel_registry", fromlist=["load_channels"]).load_channels(
            "hormozi", tmp_path
        )
    )
    assert reloaded == []
