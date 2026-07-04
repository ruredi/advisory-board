from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.pipeline.fatal_errors import PipelineCancelledError
from memory_builder.storage.sqlite_store import SQLiteStore, STOP_REASON_INTERRUPTED
from memory_builder.telemetry.context import PipelineRunContext, run_context
from memory_builder.telemetry.queries import get_run_progress
from memory_builder.telemetry.run_cancel import abort_if_run_cancelled, stop_open_run


class RunCancelTests(unittest.TestCase):
    def test_abort_if_run_cancelled_marks_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.request_run_cancel(run_id)

            with self.assertRaises(PipelineCancelledError):
                abort_if_run_cancelled(store, run_id, summary={"errors": 0})

            progress = get_run_progress(store, "hormozi", run_id)
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.status, "interrupted")
            self.assertEqual(progress.stop_reason, STOP_REASON_INTERRUPTED)

    def test_stop_open_run_sets_cancel_and_signals_pid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.set_run_pid(run_id, 4242)

            with patch("memory_builder.telemetry.run_cancel.signal_run_process", return_value=True) as signal_mock:
                self.assertTrue(stop_open_run(store, "hormozi", run_id))

            self.assertTrue(store.is_run_cancel_requested(run_id))
            signal_mock.assert_called_once_with(4242)

    def test_cancelled_run_skips_finish_sync_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            ctx = PipelineRunContext("hormozi", run_id, store)
            store.request_run_cancel(run_id)

            with self.assertRaises(PipelineCancelledError):
                with run_context(ctx):
                    abort_if_run_cancelled(store, run_id)

            self.assertFalse(store.is_run_open(run_id))


if __name__ == "__main__":
    unittest.main()
