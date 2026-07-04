from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.discovery.social_profiles import _effective_max_pages, _remaining_limit
from memory_builder.discovery.watermarks import bootstrap_profile_floor_watermark, is_newer_than
from memory_builder.fetch.scrapfly_instagram import instagram_discovery_step
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import SQLiteStore


class InstagramDiscoveryStepTests(unittest.TestCase):
    def test_forward_collects_newer_posts(self) -> None:
        phase, collect = instagram_discovery_step(
            phase="forward",
            forward_since="2026-07-01T00:00:00+00:00",
            published="2026-07-02T00:00:00+00:00",
            is_known=False,
        )
        self.assertEqual(phase, "forward")
        self.assertTrue(collect)

    def test_forward_switches_to_backward_at_watermark(self) -> None:
        phase, collect = instagram_discovery_step(
            phase="forward",
            forward_since="2026-07-02T00:00:00+00:00",
            published="2026-06-01T00:00:00+00:00",
            is_known=False,
        )
        self.assertEqual(phase, "backward")
        self.assertTrue(collect)

    def test_backward_skips_newer_than_watermark(self) -> None:
        phase, collect = instagram_discovery_step(
            phase="backward",
            forward_since="2026-07-02T00:00:00+00:00",
            published="2026-07-03T00:00:00+00:00",
            is_known=False,
        )
        self.assertEqual(phase, "backward")
        self.assertFalse(collect)

    def test_known_urls_never_collected(self) -> None:
        phase, collect = instagram_discovery_step(
            phase="forward",
            forward_since=None,
            published="2026-07-03T00:00:00+00:00",
            is_known=True,
        )
        self.assertEqual(phase, "forward")
        self.assertFalse(collect)


class DiscoveryLimitHelperTests(unittest.TestCase):
    def test_remaining_limit(self) -> None:
        self.assertIsNone(_remaining_limit(None, 10))
        self.assertIsNone(_remaining_limit(0, 10))
        self.assertEqual(_remaining_limit(100, 40), 60)
        self.assertEqual(_remaining_limit(50, 50), 0)

    def test_effective_max_pages(self) -> None:
        self.assertEqual(_effective_max_pages(50, 50), 50)
        self.assertEqual(_effective_max_pages(1000, 50), 113)
        self.assertEqual(_effective_max_pages(0, 50), 500)


class FloorWatermarkTests(unittest.TestCase):
    def test_bootstrap_profile_floor_watermark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/old/",
                    source_title="Old",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.FAILED,
                    source_date="2026-05-01T00:00:00+00:00",
                )
            )
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/new/",
                    source_title="New",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.FAILED,
                    source_date="2026-07-02T00:00:00+00:00",
                )
            )
            floor = bootstrap_profile_floor_watermark(
                store,
                "https://instagram.com/hormozi",
                platform="instagram",
            )
            self.assertEqual(floor, "2026-05-01T00:00:00+00:00")
            self.assertTrue(is_newer_than("2026-07-02T00:00:00+00:00", floor or ""))


if __name__ == "__main__":
    unittest.main()
