from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_builder.channel_registry import (
    ChannelRegistry,
    ContentChannel,
    archive_channel,
    is_channel_archived,
    load_channels,
    save_channels,
    sorted_channels,
)
from memory_builder.selected_sources import (
    add_selected_source,
    archive_selected_source,
    list_selected_sources,
)
from memory_builder.source_registry import ApprovedSources, SourceCandidate, load_approved, save_approved


class SelectedSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_path = Path(tempfile.mkdtemp())
        self.approved_file = self.tmp_path / "sources" / "approved" / "hormozi.yaml"
        self.channels_file = self.tmp_path / "sources" / "channels" / "hormozi.yaml"
        self.approved_file.parent.mkdir(parents=True)
        self.channels_file.parent.mkdir(parents=True)
        self.approved_patch = patch(
            "memory_builder.source_registry.approved_path",
            lambda persona_id, root=None: self.approved_file,
        )
        self.channels_patch = patch(
            "memory_builder.channel_registry.channels_path",
            lambda persona_id, root=None: self.channels_file,
        )
        self.approved_patch.start()
        self.channels_patch.start()

    def tearDown(self) -> None:
        self.approved_patch.stop()
        self.channels_patch.stop()

    def test_archive_selected_source_updates_approved_and_registry(self) -> None:
        approved = ApprovedSources(
            persona_id="hormozi",
            reviewed_at="2026-01-01T00:00:00+00:00",
            reviewed_by="test",
            sources=[
                SourceCandidate(
                    url="https://www.youtube.com/@test",
                    platform="youtube",
                    confidence=1.0,
                    discovery_source="manual",
                    username="test",
                    status="approved",
                )
            ],
        )
        save_approved(approved, self.tmp_path)
        registry = ChannelRegistry(
            persona_id="hormozi",
            channels=[
                ContentChannel(
                    channel_id="youtube-channel-test",
                    type="youtube_channel",
                    url="https://www.youtube.com/@test",
                    label="Test",
                )
            ],
        )
        save_channels(registry, self.tmp_path)

        archived = archive_selected_source(
            "hormozi", "youtube-channel-test", archived=True, root=self.tmp_path
        )
        self.assertTrue(archived.archived)
        reloaded = load_approved("hormozi", self.tmp_path)
        assert reloaded is not None
        self.assertTrue(reloaded.sources[0].archived)
        self.assertTrue(
            is_channel_archived(load_channels("hormozi", self.tmp_path).channels[0])
        )

    def test_add_selected_source_creates_approved_social_profile(self) -> None:
        selected = add_selected_source(
            "hormozi",
            channel_type="instagram_profile",
            url="https://instagram.com/hormozi",
            label="Hormozi IG",
            root=self.tmp_path,
        )
        self.assertEqual(selected.type, "instagram_profile")
        self.assertFalse(selected.archived)
        approved = load_approved("hormozi", self.tmp_path)
        assert approved is not None
        self.assertTrue(any("instagram.com/hormozi" in source.url for source in approved.sources))

    def test_list_selected_sources_bootstraps_spotify_from_registry(self) -> None:
        approved = ApprovedSources(
            persona_id="hormozi",
            reviewed_at="2026-01-01T00:00:00+00:00",
            reviewed_by="test",
            sources=[
                SourceCandidate(
                    url="https://x.com/alexhormozi",
                    platform="x",
                    confidence=0.96,
                    discovery_source="official_site",
                    username="alexhormozi",
                    status="approved",
                )
            ],
        )
        save_approved(approved, self.tmp_path)
        registry = ChannelRegistry(
            persona_id="hormozi",
            channels=[
                ContentChannel(
                    channel_id="spotify-show-test",
                    type="spotify_show",
                    url="https://open.spotify.com/show/abc123",
                    label="Podcast",
                )
            ],
        )
        save_channels(registry, self.tmp_path)

        items = list_selected_sources("hormozi", self.tmp_path)
        urls = [item.url for item in items]
        self.assertIn("https://x.com/alexhormozi", urls)
        self.assertIn("https://open.spotify.com/show/abc123", urls)


class ArchiveChannelTests(unittest.TestCase):
    def test_archive_channel_filters_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
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
            with patch(
                "memory_builder.channel_registry.channels_path",
                lambda persona_id, root=None: channels_file,
            ):
                save_channels(registry, tmp_path)
                archived = archive_channel("hormozi", "yt-test", archived=True, root=tmp_path)
                self.assertTrue(is_channel_archived(archived))
                reloaded = sorted_channels(load_channels("hormozi", tmp_path))
                self.assertEqual(reloaded, [])


if __name__ == "__main__":
    unittest.main()
