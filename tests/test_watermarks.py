from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.discovery.watermarks import (
    bootstrap_profile_watermark,
    filter_new_source_records,
    is_newer_than,
    parse_twitter_created_at,
    parse_unix_timestamp,
)
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.storage.sqlite_store import SQLiteStore


class WatermarkTests(unittest.TestCase):
    def test_is_newer_than(self) -> None:
        self.assertTrue(is_newer_than("2026-07-02T00:00:00+00:00", "2026-07-01T00:00:00+00:00"))
        self.assertFalse(is_newer_than("2026-07-01T00:00:00+00:00", "2026-07-02T00:00:00+00:00"))
        self.assertTrue(is_newer_than(None, "2026-07-01T00:00:00+00:00"))

    def test_parse_unix_timestamp(self) -> None:
        ts = int(datetime(2026, 7, 2, tzinfo=timezone.utc).timestamp())
        parsed = parse_unix_timestamp(ts)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.startswith("2026-07-02"))

    def test_parse_twitter_created_at(self) -> None:
        parsed = parse_twitter_created_at("Wed Jul 02 09:00:00 +0000 2026")
        self.assertIsNotNone(parsed)
        self.assertIn("2026-07-02", parsed or "")

    def test_filter_new_source_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/existing/",
                    source_title="Existing",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.FAILED,
                    channel_url="https://instagram.com/hormozi",
                )
            )
            records = [
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/existing/",
                    source_title="Existing",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.PENDING,
                ),
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://instagram.com/p/new/",
                    source_title="New",
                    source_type=SourceType.SOCIAL,
                    status=SourceStatus.PENDING,
                ),
            ]
            filtered = filter_new_source_records(store, records)
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0].source_url, "https://instagram.com/p/new/")

    def test_max_source_date_uses_discovered_at_fallback(self) -> None:
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
                    channel_url="https://instagram.com/hormozi",
                    discovered_at="2026-06-01T12:00:00+00:00",
                )
            )
            self.assertEqual(
                store.max_source_date_for_channel("https://instagram.com/hormozi"),
                "2026-06-01T12:00:00+00:00",
            )


    def test_bootstrap_profile_watermark_platform_fallback(self) -> None:
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
                    discovered_at="2026-06-01T12:00:00+00:00",
                )
            )
            watermark = bootstrap_profile_watermark(
                store,
                "https://instagram.com/hormozi",
                platform="instagram",
            )
            self.assertEqual(watermark, "2026-06-01T12:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
