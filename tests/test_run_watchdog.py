from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.context import PipelineRunContext, run_context
from memory_builder.telemetry.queries import get_run_progress
from memory_builder.telemetry.run_watchdog import (
    close_stale_runs_for_persona,
    compute_active_duration_seconds,
    resolve_run_status,
)


class RunWatchdogTests(unittest.TestCase):
    def test_mark_stale_run_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.connect().execute(
                """
                UPDATE sync_runs
                SET last_activity_at = datetime('now', '-300 seconds')
                WHERE id = ?
                """,
                (run_id,),
            )
            store.connect().commit()

            closed = close_stale_runs_for_persona(store, "hormozi", threshold_seconds=120)
            self.assertEqual(closed, [run_id])

            progress = get_run_progress(store, "hormozi", run_id)
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.status, "interrupted")
            self.assertIsNotNone(progress.stopped_at)
            self.assertEqual(progress.stop_reason, "interrupted")

    def test_successful_run_is_finished(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            ctx = PipelineRunContext("hormozi", run_id, store)
            with run_context(ctx):
                ctx.event("discovery", "Discovered 1 source")
            store.finish_sync_run(run_id, {"sources_processed": 0, "errors": 0})

            progress = get_run_progress(store, "hormozi", run_id)
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.status, "finished")
            self.assertEqual(progress.stop_reason, "finished")
            self.assertGreaterEqual(progress.active_duration_seconds, 0)

    def test_resolve_run_status(self) -> None:
        self.assertEqual(resolve_run_status({"finished_at": None}), "running")
        self.assertEqual(
            resolve_run_status({"finished_at": "2026-07-02 10:00:00", "stop_reason": "interrupted"}),
            "interrupted",
        )
        self.assertEqual(
            resolve_run_status({"finished_at": "2026-07-02 10:00:00", "stop_reason": "finished"}),
            "finished",
        )
        self.assertEqual(
            resolve_run_status({"finished_at": "2026-07-02 10:00:00", "stop_reason": "fatal_error"}),
            "aborted",
        )

    def test_active_duration_uses_stopped_at(self) -> None:
        seconds = compute_active_duration_seconds(
            {
                "started_at": "2026-07-02 10:00:00",
                "stopped_at": "2026-07-02 10:05:00",
                "finished_at": "2026-07-02 10:05:00",
                "stop_reason": "interrupted",
            }
        )
        self.assertEqual(seconds, 300)

    def test_touch_run_activity_from_background_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.connect().execute(
                "UPDATE sync_runs SET last_activity_at = datetime('now', '-120 seconds') WHERE id = ?",
                (run_id,),
            )
            store.connect().commit()
            before = store.connect().execute(
                "SELECT last_activity_at FROM sync_runs WHERE id = ?",
                (run_id,),
            ).fetchone()["last_activity_at"]

            errors: list[BaseException] = []

            def heartbeat() -> None:
                try:
                    store.touch_run_activity(run_id)
                except BaseException as exc:
                    errors.append(exc)

            thread = threading.Thread(target=heartbeat)
            thread.start()
            thread.join(timeout=2)

            self.assertEqual(errors, [])
            after = store.connect().execute(
                "SELECT last_activity_at FROM sync_runs WHERE id = ?",
                (run_id,),
            ).fetchone()["last_activity_at"]
            self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
