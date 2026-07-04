from __future__ import annotations

import unittest

from memory_builder.fetch.scrapfly_account import parse_scrapfly_account_payload
from memory_builder.telemetry.pricing import estimate_scrapfly_cost_usd
from memory_builder.telemetry.queries import cost_per_call, get_cost_breakdown, get_cost_totals, list_sync_runs


class ScrapflyAccountTests(unittest.TestCase):
    def test_parse_scrapfly_account_payload(self) -> None:
        payload = {
            "project": {
                "name": "default",
                "quota_reached": True,
            },
            "subscription": {
                "plan_name": "DISCOVERY",
                "period": {"start": "2026-06-03", "end": "2026-07-03"},
                "billing": {"plan_price": {"amount": "30", "currency": "USD"}},
                "usage": {
                    "scrape": {
                        "current": 12500,
                        "limit": 200000,
                        "remaining": 187500,
                        "concurrent_usage": 1,
                        "concurrent_limit": 5,
                    }
                },
            },
        }
        info = parse_scrapfly_account_payload(payload)
        self.assertEqual(info.plan_name, "DISCOVERY")
        self.assertEqual(info.period_end, "2026-07-03")
        self.assertEqual(info.credits_used, 12500)
        self.assertEqual(info.credits_remaining, 187500)
        self.assertEqual(info.plan_price_usd, 30.0)
        self.assertAlmostEqual(info.usage_usd, 12500 * (30.0 / 200_000), places=6)
        self.assertTrue(info.quota_reached)


class CostQueryFilterTests(unittest.TestCase):
    def test_provider_filters_and_cost_per_call(self) -> None:
        import tempfile
        from pathlib import Path

        from memory_builder.storage.sqlite_store import SQLiteStore

        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.log_api_usage(
                persona_id="hormozi",
                run_id=run_id,
                source_id=None,
                provider="google",
                operation="extraction",
                model="gemini-2.5-flash",
                input_tokens=1000,
                output_tokens=100,
                cost_usd=0.02,
            )
            store.log_api_usage(
                persona_id="hormozi",
                run_id=run_id,
                source_id=None,
                provider="scrapfly",
                operation="twitter_scrape",
                api_credits=25,
                cost_usd=0.01,
            )
            store.finish_sync_run(run_id, {"sources_processed": 1})

            scrapfly = get_cost_totals(store, "hormozi", provider="scrapfly")
            api_only = get_cost_totals(store, "hormozi", exclude_provider="scrapfly")
            self.assertEqual(scrapfly.call_count, 1)
            self.assertEqual(scrapfly.api_credits, 25)
            self.assertEqual(api_only.call_count, 1)
            self.assertEqual(api_only.input_tokens, 1000)

            breakdown = get_cost_breakdown(
                store,
                "hormozi",
                group_by="provider",
                exclude_provider="scrapfly",
            )
            self.assertEqual(len(breakdown), 1)
            self.assertEqual(breakdown[0]["label"], "google")

            self.assertAlmostEqual(cost_per_call(0.01, 1) or 0, 0.01)
            self.assertIsNone(cost_per_call(0.01, 0))

    def test_run_list_uses_live_cost_including_scrapfly(self) -> None:
        import tempfile
        from pathlib import Path

        from memory_builder.storage.sqlite_store import SQLiteStore

        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            run_id = store.start_sync_run()
            store.log_api_usage(
                persona_id="hormozi",
                run_id=run_id,
                source_id=None,
                provider="google",
                operation="extraction",
                model="gemini-2.5-flash",
                cost_usd=0.02,
            )
            scrapfly_cost = estimate_scrapfly_cost_usd(credits=8214)
            store.log_api_usage(
                persona_id="hormozi",
                run_id=run_id,
                source_id=None,
                provider="scrapfly",
                operation="twitter_scrape",
                api_credits=8214,
                cost_usd=scrapfly_cost,
            )
            store.mark_run_interrupted(run_id)

            runs = list_sync_runs(store, "hormozi")
            self.assertEqual(len(runs), 1)
            self.assertAlmostEqual(runs[0]["cost_usd_display"], 0.02 + scrapfly_cost, places=6)
            row = store.connect().execute(
                "SELECT cost_usd FROM sync_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            self.assertAlmostEqual(float(row["cost_usd"]), 0.02 + scrapfly_cost, places=6)


if __name__ == "__main__":
    unittest.main()
