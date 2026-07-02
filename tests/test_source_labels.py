from __future__ import annotations

import unittest

from memory_builder.models import SourceType
from memory_builder.telemetry.source_labels import extract_stage_label, platform_label, short_url, stage_label


class SourceLabelTests(unittest.TestCase):
    def test_spotify_platform(self) -> None:
        self.assertEqual(
            platform_label(
                SourceType.PODCAST,
                "https://episode.flightcast.com/foo.mp3",
                channel_url="https://open.spotify.com/show/abc",
            ),
            "Spotify",
        )

    def test_podcast_platform(self) -> None:
        self.assertEqual(
            platform_label(SourceType.PODCAST, "https://example.com/feed/item"),
            "Podcast",
        )

    def test_youtube_platform(self) -> None:
        self.assertEqual(
            platform_label(SourceType.YOUTUBE, "https://youtube.com/watch?v=abc"),
            "YouTube",
        )

    def test_social_x(self) -> None:
        self.assertEqual(platform_label(SourceType.SOCIAL, "https://x.com/alexhormozi/status/1"), "X")

    def test_social_instagram(self) -> None:
        self.assertEqual(platform_label(SourceType.SOCIAL, "https://instagram.com/p/abc/"), "Instagram")

    def test_short_url(self) -> None:
        self.assertEqual(
            short_url("https://episode.flightcast.com/zz5nwp81tktx53wb8fw6qq7j/episode.mp3"),
            "episode.flightcast.com/zz5nwp81tktx53wb8fw6qq7j/episode.mp3",
        )

    def test_extract_stage_label_with_chunks(self) -> None:
        self.assertEqual(
            extract_stage_label("source_extract", {"chunk_index": 2, "chunk_total": 7}),
            "extracting chunk 2/7",
        )

    def test_extract_stage_label_fallback(self) -> None:
        self.assertEqual(extract_stage_label("source_fetch", {}), stage_label("source_fetch"))


if __name__ == "__main__":
    unittest.main()
