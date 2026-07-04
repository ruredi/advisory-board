from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.pipeline.fatal_errors import (
    FatalErrorTracker,
    classify_fatal_error,
    is_transient_error,
)
from memory_builder.pipeline.initial_build import MemoryPipeline
from memory_builder.storage.sqlite_store import SQLiteStore, STOP_REASON_FATAL_ERROR
from memory_builder.telemetry.queries import get_run_progress
from memory_builder.telemetry.run_watchdog import resolve_run_status


class FatalErrorTests(unittest.TestCase):
    def test_classify_server_disconnected(self) -> None:
        self.assertEqual(
            classify_fatal_error("Server disconnected without sending a response."),
            "server_disconnected",
        )

    def test_non_fatal_error_is_none(self) -> None:
        self.assertIsNone(classify_fatal_error("Video unavailable"))

    def test_transient_errors_do_not_abort_batch(self) -> None:
        tracker = FatalErrorTracker(threshold=2)
        fatal = RuntimeError("Server disconnected without sending a response.")
        for _ in range(5):
            self.assertFalse(tracker.record(fatal))

    def test_immediate_fatal_for_auth(self) -> None:
        tracker = FatalErrorTracker()
        self.assertTrue(tracker.record(RuntimeError("401 Unauthorized: invalid api key")))

    def test_mark_run_aborted_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.mark_run_stopped(
                run_id,
                reason=STOP_REASON_FATAL_ERROR,
                event_stage="run_aborted",
                message="Pipeline stopped after repeated fatal errors",
                summary={"errors": 2, "sources_processed": 0},
            )

            progress = get_run_progress(store, "hormozi", run_id)
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.status, "aborted")
            self.assertEqual(progress.stop_reason, "fatal_error")

    def test_summary_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = MemoryPipeline("hormozi", Path(tmp))
            pipeline.summary.errors = 2
            pipeline.summary.sources_processed = 5
            summary = pipeline.summary_dict()
            self.assertEqual(summary["errors"], 2)
            self.assertEqual(summary["sources_processed"], 5)

    def test_resolve_run_status_aborted(self) -> None:
        self.assertEqual(
            resolve_run_status({"finished_at": "2026-07-02 10:00:00", "stop_reason": "fatal_error"}),
            "aborted",
        )


if __name__ == "__main__":
    unittest.main()
