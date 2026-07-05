from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.models import MediaFormat, SourceRecord, SourceStatus, SourceType
from memory_builder.pipeline.platform_filter import (
    media_format_sql_filter,
    normalize_media_filter,
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


class MediaFilterTests(unittest.TestCase):
    def test_normalize_media_filter(self) -> None:
        self.assertEqual(normalize_media_filter("Video"), "video")
        with self.assertRaises(ValueError):
            normalize_media_filter("gif")

    def test_media_format_sql_filter(self) -> None:
        self.assertEqual(media_format_sql_filter(None), ("", []))
        self.assertEqual(media_format_sql_filter("image"), (" AND media_format = ?", ["image"]))

    def test_list_pending_by_media_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/reel/vid1",
                    source_title="Reel",
                    source_type=SourceType.SOCIAL,
                    media_format=MediaFormat.VIDEO,
                    status=SourceStatus.PENDING,
                )
            )
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/img1",
                    source_title="Photo",
                    source_type=SourceType.SOCIAL,
                    media_format=MediaFormat.IMAGE,
                    status=SourceStatus.PENDING,
                )
            )
            video_rows = store.list_pending_sources_ordered(media_format="video")
            self.assertEqual(len(video_rows), 1)
            self.assertEqual(video_rows[0]["media_format"], MediaFormat.VIDEO)

            image_rows = store.list_pending_sources_ordered(media_format="image")
            self.assertEqual(len(image_rows), 1)
            self.assertEqual(image_rows[0]["media_format"], MediaFormat.IMAGE)

            combined = store.list_pending_sources_ordered(platform="instagram", media_format="video")
            self.assertEqual(len(combined), 1)

    def test_update_source_metadata_persists_media_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            source_id = store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/x",
                    source_title="Post",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.PENDING,
                )
            )
            row = store.get_source_by_url("https://instagram.com/p/x")
            self.assertEqual(row["media_format"], MediaFormat.UNKNOWN)
            store.update_source_metadata(source_id, media_format=MediaFormat.IMAGE)
            row = store.get_source_by_url("https://instagram.com/p/x")
            self.assertEqual(row["media_format"], MediaFormat.IMAGE)


if __name__ == "__main__":
    unittest.main()
