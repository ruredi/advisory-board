from __future__ import annotations

from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.queries import (
    get_cost_totals,
    get_run_activity,
)

from api.personas import get_persona_config
from api.schemas import ActiveRun, CostSummary, PersonaOverview, RunSummary


def _source_status_counts(store: SQLiteStore, persona_id: str) -> dict[str, int]:
    rows = store.connect().execute(
        "SELECT status, COUNT(*) AS c FROM sources WHERE persona_id = ? GROUP BY status",
        (persona_id,),
    ).fetchall()
    return {str(row["status"]): int(row["c"]) for row in rows}


def _unit_count(store: SQLiteStore, persona_id: str) -> int:
    row = store.connect().execute(
        "SELECT COUNT(*) AS c FROM knowledge_units WHERE persona_id = ?",
        (persona_id,),
    ).fetchone()
    return int(row["c"])


def _last_run(store: SQLiteStore, persona_id: str) -> RunSummary | None:
    row = store.connect().execute(
        """
        SELECT id, started_at, finished_at, sources_discovered, sources_processed,
               units_created, errors, cost_usd
        FROM sync_runs
        WHERE persona_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (persona_id,),
    ).fetchone()
    if row is None:
        return None
    return RunSummary(
        run_id=int(row["id"]),
        started_at=str(row["started_at"]),
        finished_at=row["finished_at"],
        sources_discovered=int(row["sources_discovered"] or 0),
        sources_processed=int(row["sources_processed"] or 0),
        units_created=int(row["units_created"] or 0),
        errors=int(row["errors"] or 0),
        cost_usd=float(row["cost_usd"] or 0),
    )


def _active_run(store: SQLiteStore, persona_id: str) -> ActiveRun | None:
    row = store.connect().execute(
        """
        SELECT id, started_at
        FROM sync_runs
        WHERE persona_id = ? AND finished_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (persona_id,),
    ).fetchone()
    if row is None:
        return None
    run_id = int(row["id"])
    latest = store.connect().execute(
        "SELECT stage, message FROM pipeline_events WHERE run_id = ? ORDER BY id DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    activity = get_run_activity(store, persona_id, run_id)
    cost_run = get_cost_totals(store, persona_id, run_id=run_id)
    return ActiveRun(
        run_id=run_id,
        started_at=str(row["started_at"]),
        latest_stage=str(latest["stage"]) if latest else "",
        latest_message=str(latest["message"]) if latest else "",
        current_platform=activity.current_platform,
        current_title=activity.current_title,
        current_url=activity.current_url,
        current_stage=activity.current_stage,
        done_count=activity.done_count,
        error_count=activity.error_count,
        skip_count=activity.skip_count,
        pending_by_platform=activity.pending_by_platform,
        cost_run_usd=cost_run.cost_usd,
    )


def build_persona_overview(persona_id: str) -> PersonaOverview:
    config = get_persona_config(persona_id)
    store = SQLiteStore(persona_id)
    try:
        store.initialize()
        status_counts = _source_status_counts(store, persona_id)
        cost_today = get_cost_totals(store, persona_id, day="now")
        cost_total = get_cost_totals(store, persona_id)
        return PersonaOverview(
            persona_id=persona_id,
            display_name=config.display_name,
            source_status_counts=status_counts,
            source_total=sum(status_counts.values()),
            unit_count=_unit_count(store, persona_id),
            cost=CostSummary(
                today_usd=cost_today.cost_usd,
                today_calls=cost_today.call_count,
                total_usd=cost_total.cost_usd,
                total_calls=cost_total.call_count,
            ),
            last_run=_last_run(store, persona_id),
            active_run=_active_run(store, persona_id),
        )
    finally:
        store.close()
