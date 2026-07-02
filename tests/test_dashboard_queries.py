from __future__ import annotations

from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.queries import get_cost_breakdown, list_sync_runs


def test_list_sync_runs_and_cost_breakdown(tmp_path, monkeypatch):
    db = tmp_path / "hormozi.sqlite"
    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: db,
    )
    store = SQLiteStore("hormozi")
    store.initialize()
    run_id = store.start_sync_run()
    store.log_api_usage(
        persona_id="hormozi",
        run_id=run_id,
        source_id=None,
        provider="google",
        operation="extraction",
        model="gemini-2.5-flash",
        cost_usd=0.01,
    )
    store.finish_sync_run(run_id, {"sources_processed": 1})
    runs = list_sync_runs(store, "hormozi")
    assert len(runs) == 1
    assert runs[0]["id"] == run_id
    breakdown = get_cost_breakdown(store, "hormozi", group_by="provider")
    assert breakdown[0]["label"] == "google"
    assert breakdown[0]["cost_usd"] == 0.01
    store.close()
