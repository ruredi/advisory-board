from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.context import PipelineRunContext, run_context
from memory_builder.telemetry.pricing import (
    estimate_gemini_cost_usd,
    estimate_openai_embedding_cost_usd,
    estimate_scrapfly_cost_usd,
)
from memory_builder.telemetry.queries import get_cost_totals, get_run_progress, list_pipeline_events


class TelemetryTests(unittest.TestCase):
    def test_schema_and_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            ctx = PipelineRunContext("hormozi", run_id, store)
            with run_context(ctx):
                ctx.event("discovery", "Discovered 3 sources", metadata={"count": 3})
                ctx.record_api_usage(
                    provider="google",
                    operation="extraction",
                    model="gemini-2.5-flash",
                    input_tokens=1000,
                    output_tokens=200,
                    cost_usd=estimate_gemini_cost_usd(
                        model="gemini-2.5-flash",
                        input_tokens=1000,
                        output_tokens=200,
                    ),
                )
                ctx.record_api_usage(
                    provider="openai",
                    operation="embedding",
                    model="text-embedding-3-small",
                    input_tokens=500,
                    cost_usd=estimate_openai_embedding_cost_usd(
                        model="text-embedding-3-small",
                        input_tokens=500,
                    ),
                    is_estimated=False,
                )
                ctx.record_api_usage(
                    provider="scrapfly",
                    operation="twitter_scrape",
                    api_credits=25,
                    cost_usd=estimate_scrapfly_cost_usd(credits=25),
                )
            store.finish_sync_run(run_id, {"sources_processed": 1, "errors": 0})

            events = list_pipeline_events(store, "hormozi", run_id=run_id)
            self.assertGreaterEqual(len(events), 3)  # run_started, discovery, run_finished
            stages = {event["stage"] for event in events}
            self.assertIn("discovery", stages)
            self.assertIn("run_started", stages)

            cost_run = get_cost_totals(store, "hormozi", run_id=run_id)
            self.assertGreater(cost_run.cost_usd, 0)
            self.assertEqual(cost_run.call_count, 3)

            progress = get_run_progress(store, "hormozi", run_id)
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.run_id, run_id)
            self.assertGreater(progress.cost_run_usd, 0)
            self.assertIsNotNone(progress.finished_at)

            run_row = store.connect().execute("SELECT cost_usd FROM sync_runs WHERE id = ?", (run_id,)).fetchone()
            self.assertAlmostEqual(float(run_row["cost_usd"]), cost_run.cost_usd, places=6)


if __name__ == "__main__":
    unittest.main()
