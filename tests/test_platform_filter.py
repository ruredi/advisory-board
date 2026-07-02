from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.pipeline.platform_filter import (
    normalize_platform_filter,
    platform_sql_filter,
    social_profile_matches_filter,
)
from memory_builder.storage.sqlite_store import SQLiteStore


class PlatformFilterTests(unittest.TestCase):
    def test_normalize_twitter_alias(self) -> None:
        self.assertEqual(normalize_platform_filter("twitter"), "x")

    def test_unsupported_raises(self) -> None:
        with self.assertRaises(ValueError):
            normalize_platform_filter("tiktok")

    def test_social_profile_matches_filter(self) -> None:
        self.assertTrue(social_profile_matches_filter("instagram", None))
        self.assertTrue(social_profile_matches_filter("instagram", "instagram"))
        self.assertFalse(social_profile_matches_filter("x", "instagram"))
        self.assertTrue(social_profile_matches_filter("twitter", "x"))
        self.assertFalse(social_profile_matches_filter("facebook", "instagram"))


class PlatformPendingFilterTests(unittest.TestCase):
    def test_list_pending_by_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://youtube.com/watch?v=abc",
                    source_title="YT",
                    source_type=SourceType.YOUTUBE,
                    status=SourceStatus.PENDING,
                )
            )
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://episode.flightcast.com/ep.mp3",
                    source_title="Pod",
                    source_type=SourceType.PODCAST,
                    status=SourceStatus.PENDING,
                    channel_url="https://open.spotify.com/show/abc",
                )
            )
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://x.com/user/status/1",
                    source_title="Tweet",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.PENDING,
                )
            )
            yt_rows = store.list_pending_sources_ordered(platform="youtube")
            self.assertEqual(len(yt_rows), 1)
            self.assertEqual(yt_rows[0]["source_type"], SourceType.YOUTUBE)

            spotify_rows = store.list_pending_sources_ordered(platform="spotify")
            self.assertEqual(len(spotify_rows), 1)

            x_rows = store.list_pending_sources_ordered(platform="x")
            self.assertEqual(len(x_rows), 1)


if __name__ == "__main__":
    unittest.main()
