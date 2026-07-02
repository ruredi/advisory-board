from __future__ import annotations

import unittest
from unittest.mock import patch

import feedparser

from memory_builder.channel_registry import (
    CHANNEL_TYPE_PRIORITY,
    add_channel,
    bootstrap_channels_from_config,
    channel_id_from_url,
    load_channels,
)
from memory_builder.dedup.title_dedup import normalize_episode_title, titles_likely_match
from memory_builder.discovery.podcast_rss import discover_podcast_rss_feed, resolve_apple_podcast_rss
from memory_builder.models import SourceStatus


class TitleDedupTests(unittest.TestCase):
    def test_normalize_episode_title_strips_ep_number(self) -> None:
        title = "3 Levels of Building a Personal Brand | Ep 984"
        self.assertEqual(
            normalize_episode_title(title),
            "3 levels of building a personal brand",
        )

    def test_titles_likely_match_youtube_podcast(self) -> None:
        youtube = "3 Levels of Building a Personal Brand"
        podcast = "3 Levels of Building a Personal Brand | Ep 984"
        self.assertTrue(titles_likely_match(youtube, podcast))


class ChannelRegistryTests(unittest.TestCase):
    def test_bootstrap_youtube_from_watch_feeds(self) -> None:
        registry = bootstrap_channels_from_config("hormozi")
        types = {channel.type for channel in registry.channels}
        self.assertIn("youtube_channel", types)

    def test_channel_id_slug(self) -> None:
        channel_id = channel_id_from_url(
            "spotify_show",
            "https://open.spotify.com/show/6YNopzKDGDwf0auIpPTIID",
        )
        self.assertTrue(channel_id.startswith("spotify-show-"))

    def test_spotify_priority_after_youtube(self) -> None:
        self.assertLess(
            CHANNEL_TYPE_PRIORITY["youtube_channel"],
            CHANNEL_TYPE_PRIORITY["spotify_show"],
        )


class PodcastRssTests(unittest.TestCase):
    @patch("memory_builder.discovery.podcast_rss.httpx.get")
    def test_resolve_apple_podcast_rss(self, mock_get) -> None:
        class Response:
            def raise_for_status(self) -> None:
                return None

            def json(self):
                return {
                    "results": [
                        {
                            "feedUrl": "https://rss.example.com/feed.xml",
                            "collectionId": 1254720112,
                        }
                    ]
                }

        mock_get.return_value = Response()
        rss_url, podcast_id = resolve_apple_podcast_rss(
            "https://podcasts.apple.com/us/podcast/the-game-with-alex-hormozi/id1254720112"
        )
        self.assertEqual(rss_url, "https://rss.example.com/feed.xml")
        self.assertEqual(podcast_id, "1254720112")

    def test_discover_podcast_rss_respects_watermark(self) -> None:
        feed = """<?xml version='1.0' encoding='UTF-8'?>
        <rss version="2.0"><channel><title>Test</title>
        <item>
          <title>Old Episode | Ep 1</title>
          <pubDate>Mon, 01 Jan 2024 09:00:00 -0000</pubDate>
          <enclosure url="https://episode.flightcast.com/old.mp3" type="audio/mpeg"/>
        </item>
        <item>
          <title>New Episode | Ep 2</title>
          <pubDate>Thu, 02 Jul 2026 09:00:00 -0000</pubDate>
          <enclosure url="https://episode.flightcast.com/new.mp3" type="audio/mpeg"/>
        </item>
        </channel></rss>"""

        with patch("memory_builder.discovery.podcast_rss.feedparser.parse", return_value=feedparser.parse(feed)):
            records, max_published = discover_podcast_rss_feed(
                "hormozi",
                "https://rss.example.com/feed.xml",
                channel_url="https://open.spotify.com/show/test",
                seen=set(),
                watermark="2025-01-01T00:00:00+00:00",
            )
        self.assertEqual(len(records), 1)
        self.assertIn("New Episode", records[0].source_title)
        self.assertEqual(records[0].status, SourceStatus.PENDING)
        self.assertIsNotNone(max_published)


if __name__ == "__main__":
    unittest.main()
