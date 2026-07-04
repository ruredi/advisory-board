from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from memory_builder.models import json_loads
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.run_mode import PROCESSING_STAGES, resolve_run_mode
from memory_builder.telemetry.run_watchdog import compute_active_duration_seconds, resolve_run_status
from memory_builder.telemetry.source_labels import extract_stage_label, platform_label, short_url


@dataclass(frozen=True)
class CostTotals:
    cost_usd: float
    input_tokens: int
    output_tokens: int
    api_credits: float
    call_count: int


@dataclass(frozen=True)
class RunProgress:
    run_id: int
    persona_id: str
    started_at: str
    finished_at: str | None
    latest_stage: str
    latest_message: str
    events_count: int
    sources_processed: int
    cost_run_usd: float
    cost_persona_usd: float
    cost_today_usd: float
    sources_discovered: int = 0
    run_mode: str = "—"
    status: str = "finished"
    stopped_at: str | None = None
    stop_reason: str | None = None
    last_activity_at: str | None = None
    active_duration_seconds: int = 0
    current_platform: str = ""
    current_title: str = ""
    current_url: str = ""
    current_stage: str = ""
    done_count: int = 0
    error_count: int = 0
    skip_count: int = 0


@dataclass(frozen=True)
class RunActivity:
    current_platform: str
    current_title: str
    current_url: str
    current_stage: str
    done_count: int
    error_count: int
    skip_count: int
    pending_by_platform: dict[str, int]


def get_cost_totals(
    store: SQLiteStore,
    persona_id: str,
    *,
    run_id: int | None = None,
    day: str | None = None,
    provider: str | None = None,
    exclude_provider: str | None = None,
) -> CostTotals:
    query = """
        SELECT
            COALESCE(SUM(cost_usd), 0) AS cost_usd,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(api_credits), 0) AS api_credits,
            COUNT(*) AS call_count
        FROM api_usage_logs
        WHERE persona_id = ?
    """
    params: list[Any] = [persona_id]
    if run_id is not None:
        query += " AND run_id = ?"
        params.append(run_id)
    if day is not None:
        query += " AND date(created_at) = date(?)"
        params.append(day)
    if provider is not None:
        query += " AND provider = ?"
        params.append(provider)
    if exclude_provider is not None:
        query += " AND provider != ?"
        params.append(exclude_provider)
    row = store.connect().execute(query, params).fetchone()
    return CostTotals(
        cost_usd=float(row["cost_usd"]),
        input_tokens=int(row["input_tokens"]),
        output_tokens=int(row["output_tokens"]),
        api_credits=float(row["api_credits"]),
        call_count=int(row["call_count"]),
    )


def list_pipeline_events(
    store: SQLiteStore,
    persona_id: str,
    *,
    run_id: int | None = None,
    after_id: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = """
        SELECT id, persona_id, run_id, source_id, stage, message, metadata_json, created_at
        FROM pipeline_events
        WHERE persona_id = ? AND id > ?
    """
    params: list[Any] = [persona_id, after_id]
    if run_id is not None:
        query += " AND run_id = ?"
        params.append(run_id)
    query += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    rows = store.connect().execute(query, params).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        raw_meta = item.pop("metadata_json", "{}")
        try:
            item["metadata"] = json_loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
        except (TypeError, ValueError):
            item["metadata"] = {}
        events.append(item)
    return events


def _event_counts(store: SQLiteStore, run_id: int) -> tuple[int, int, int]:
    rows = store.connect().execute(
        """
        SELECT stage, COUNT(*) AS c
        FROM pipeline_events
        WHERE run_id = ? AND stage IN ('source_done', 'source_error', 'source_skip')
        GROUP BY stage
        """,
        (run_id,),
    ).fetchall()
    counts = {str(row["stage"]): int(row["c"]) for row in rows}
    return counts.get("source_done", 0), counts.get("source_error", 0), counts.get("source_skip", 0)


def _non_empty_options(options: dict[str, Any] | None) -> dict[str, Any] | None:
    return options if options else None


def _phase_flags(
    phase_flags_by_run: dict[int, dict[str, bool]],
    run_id: int,
) -> dict[str, bool]:
    flags = phase_flags_by_run.get(run_id, {})
    return {
        "had_discovery": bool(flags.get("had_discovery")),
        "had_processing": bool(flags.get("had_processing")),
        "had_run_started": bool(flags.get("had_run_started")),
    }


def _run_started_options_batch(store: SQLiteStore, run_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not run_ids:
        return {}
    placeholders = ",".join("?" for _ in run_ids)
    rows = store.connect().execute(
        f"""
        SELECT run_id, metadata_json
        FROM pipeline_events
        WHERE run_id IN ({placeholders}) AND stage = 'run_started'
        ORDER BY id ASC
        """,
        run_ids,
    ).fetchall()
    options_by_run: dict[int, dict[str, Any]] = {}
    for row in rows:
        run_id = int(row["run_id"])
        if run_id in options_by_run:
            continue
        raw_meta = row["metadata_json"]
        try:
            options_by_run[run_id] = json_loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
        except (TypeError, ValueError):
            options_by_run[run_id] = {}
    return options_by_run


def _run_phase_flags_batch(store: SQLiteStore, run_ids: list[int]) -> dict[int, dict[str, bool]]:
    if not run_ids:
        return {}
    placeholders = ",".join("?" for _ in run_ids)
    processing_placeholders = ",".join("?" for _ in PROCESSING_STAGES)
    rows = store.connect().execute(
        f"""
        SELECT
            run_id,
            MAX(CASE WHEN stage = 'discovery' THEN 1 ELSE 0 END) AS had_discovery,
            MAX(CASE WHEN stage IN ({processing_placeholders}) THEN 1 ELSE 0 END) AS had_processing,
            MAX(CASE WHEN stage = 'run_started' THEN 1 ELSE 0 END) AS had_run_started
        FROM pipeline_events
        WHERE run_id IN ({placeholders})
        GROUP BY run_id
        """,
        [*PROCESSING_STAGES, *run_ids],
    ).fetchall()
    return {
        int(row["run_id"]): {
            "had_discovery": bool(row["had_discovery"]),
            "had_processing": bool(row["had_processing"]),
            "had_run_started": bool(row["had_run_started"]),
        }
        for row in rows
    }


def get_source_display_map(
    store: SQLiteStore,
    source_ids: list[int],
    *,
    persona_id: str | None = None,
) -> dict[int, dict[str, str]]:
    if not source_ids:
        return {}
    placeholders = ",".join("?" for _ in source_ids)
    rows = store.connect().execute(
        f"""
        SELECT id, source_type, source_url, source_title, channel_url
        FROM sources WHERE id IN ({placeholders})
        """,
        source_ids,
    ).fetchall()
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        source_type = str(row["source_type"])
        source_url = str(row["source_url"])
        channel_url = str(row["channel_url"]) if row["channel_url"] else ""
        platform = platform_label(source_type, source_url, channel_url=channel_url)
        result[int(row["id"])] = {
            "platform": platform,
            "title": str(row["source_title"] or ""),
            "url": source_url,
        }
    return result


def get_source_platform_map(store: SQLiteStore, source_ids: list[int]) -> dict[int, str]:
    return {source_id: info["platform"] for source_id, info in get_source_display_map(store, source_ids).items()}


def get_pending_by_platform(store: SQLiteStore, persona_id: str) -> dict[str, int]:
    rows = store.connect().execute(
        """
        SELECT source_type, source_url, channel_url, COUNT(*) AS c
        FROM sources
        WHERE persona_id = ? AND status IN ('pending', 'processing', 'failed')
        GROUP BY source_type, source_url, channel_url
        """,
        (persona_id,),
    ).fetchall()
    totals: dict[str, int] = {}
    for row in rows:
        label = platform_label(
            str(row["source_type"]),
            str(row["source_url"]),
            channel_url=str(row["channel_url"]) if row["channel_url"] else "",
        )
        totals[label] = totals.get(label, 0) + int(row["c"])
    return dict(sorted(totals.items(), key=lambda item: (-item[1], item[0])))


def get_run_activity(store: SQLiteStore, persona_id: str, run_id: int) -> RunActivity:
    done_count, error_count, skip_count = _event_counts(store, run_id)
    pending_by_platform = get_pending_by_platform(store, persona_id)

    starts = store.connect().execute(
        """
        SELECT id, source_id, stage, message, metadata_json
        FROM pipeline_events
        WHERE run_id = ? AND stage = 'source_start'
        ORDER BY id DESC
        LIMIT 20
        """,
        (run_id,),
    ).fetchall()

    current_platform = ""
    current_title = ""
    current_url = ""
    current_stage = ""

    for start in starts:
        source_id = start["source_id"]
        if source_id is None:
            continue
        terminal = store.connect().execute(
            """
            SELECT 1 FROM pipeline_events
            WHERE run_id = ? AND source_id = ? AND stage IN ('source_done', 'source_error', 'source_skip')
              AND id > ?
            LIMIT 1
            """,
            (run_id, source_id, start["id"]),
        ).fetchone()
        if terminal:
            continue
        meta = json_loads(start["metadata_json"] or "{}")
        latest = store.connect().execute(
            """
            SELECT stage, message, metadata_json FROM pipeline_events
            WHERE run_id = ? AND source_id = ? AND id >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_id, source_id, start["id"]),
        ).fetchone()
        source_row = store.connect().execute(
            "SELECT source_type, source_url, source_title, channel_url FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        source_type = str(meta.get("source_type") or (source_row["source_type"] if source_row else ""))
        current_url = str(meta.get("source_url") or (source_row["source_url"] if source_row else ""))
        channel_url = str(meta.get("channel_url") or (source_row["channel_url"] if source_row else "") or "")
        current_title = (
            str(meta.get("title", ""))
            or (str(source_row["source_title"]) if source_row and source_row["source_title"] else "")
            or str(start["message"]).removeprefix("Processing: ")
        )
        current_platform = str(meta.get("platform", "")) or platform_label(
            source_type,
            current_url,
            channel_url=channel_url,
        )
        if latest:
            latest_meta = json_loads(latest["metadata_json"] or "{}")
            current_stage = extract_stage_label(str(latest["stage"]), latest_meta)
        else:
            current_stage = "processing"
        break

    return RunActivity(
        current_platform=current_platform,
        current_title=current_title,
        current_url=current_url,
        current_stage=current_stage,
        done_count=done_count,
        error_count=error_count,
        skip_count=skip_count,
        pending_by_platform=pending_by_platform,
    )


def get_run_progress(store: SQLiteStore, persona_id: str, run_id: int) -> RunProgress | None:
    run = store.connect().execute(
        "SELECT * FROM sync_runs WHERE id = ? AND persona_id = ?",
        (run_id, persona_id),
    ).fetchone()
    if run is None:
        return None
    latest = store.connect().execute(
        """
        SELECT stage, message
        FROM pipeline_events
        WHERE run_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (run_id,),
    ).fetchone()
    events_count = store.connect().execute(
        "SELECT COUNT(*) AS c FROM pipeline_events WHERE run_id = ?",
        (run_id,),
    ).fetchone()["c"]
    cost_run = get_cost_totals(store, persona_id, run_id=run_id)
    cost_persona = get_cost_totals(store, persona_id)
    cost_today = get_cost_totals(store, persona_id, day="now")
    activity = get_run_activity(store, persona_id, run_id)
    run_row = dict(run)
    status = resolve_run_status(run_row)
    sources_discovered = int(run["sources_discovered"] or 0)
    sources_processed_db = int(run["sources_processed"] or 0)
    sources_processed_display = (
        activity.done_count
        if run["finished_at"] is None or sources_processed_db == 0
        else sources_processed_db
    )
    run_options = _non_empty_options(_run_started_options_batch(store, [run_id]).get(run_id))
    phase_flags = _phase_flags(_run_phase_flags_batch(store, [run_id]), run_id)
    run_mode = resolve_run_mode(
        options=run_options,
        sources_discovered=sources_discovered,
        sources_processed=sources_processed_display,
        **phase_flags,
    )
    return RunProgress(
        run_id=run_id,
        persona_id=persona_id,
        started_at=str(run["started_at"]),
        finished_at=run["finished_at"],
        latest_stage=str(latest["stage"]) if latest else "",
        latest_message=str(latest["message"]) if latest else "",
        events_count=int(events_count),
        sources_processed=sources_processed_display,
        sources_discovered=sources_discovered,
        run_mode=run_mode,
        cost_run_usd=cost_run.cost_usd,
        cost_persona_usd=cost_persona.cost_usd,
        cost_today_usd=cost_today.cost_usd,
        status=status,
        stopped_at=run["stopped_at"] if "stopped_at" in run.keys() else None,
        stop_reason=run["stop_reason"] if "stop_reason" in run.keys() else None,
        last_activity_at=run["last_activity_at"] if "last_activity_at" in run.keys() else None,
        active_duration_seconds=compute_active_duration_seconds(run_row),
        current_platform=activity.current_platform,
        current_title=activity.current_title,
        current_url=activity.current_url,
        current_stage=activity.current_stage,
        done_count=activity.done_count,
        error_count=activity.error_count,
        skip_count=activity.skip_count,
    )


def list_sync_runs(
    store: SQLiteStore,
    persona_id: str,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = store.connect().execute(
        """
        SELECT id, persona_id, started_at, finished_at, last_activity_at, stopped_at, stop_reason,
               sources_discovered, sources_processed,
               units_created, units_skipped_duplicate, errors, cost_usd, summary
        FROM sync_runs
        WHERE persona_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (persona_id, limit),
    ).fetchall()
    run_ids = [int(row["id"]) for row in rows]
    options_by_run = _run_started_options_batch(store, run_ids)
    phase_flags_by_run = _run_phase_flags_batch(store, run_ids)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        run_id = int(item["id"])
        done_count, error_count, skip_count = _event_counts(store, run_id)
        live_cost = get_cost_totals(store, persona_id, run_id=run_id)
        item["done_count"] = done_count
        item["error_count"] = error_count
        item["skip_count"] = skip_count
        item["live_cost_usd"] = live_cost.cost_usd
        item["api_calls"] = live_cost.call_count
        # Prefer live telemetry for list views; DB columns update only at run finish.
        if item["finished_at"] is None or int(item["sources_processed"] or 0) == 0:
            item["sources_processed_display"] = done_count
        else:
            item["sources_processed_display"] = int(item["sources_processed"])
        # api_usage_logs is the source of truth (LLM + Scrapfly USD estimates).
        item["cost_usd_display"] = live_cost.cost_usd
        if int(item["errors"] or 0) < error_count:
            item["errors_display"] = error_count
        else:
            item["errors_display"] = int(item["errors"] or 0)
        item["status"] = resolve_run_status(item)
        item["active_duration_seconds"] = compute_active_duration_seconds(item)
        item["run_mode"] = resolve_run_mode(
            options=_non_empty_options(options_by_run.get(run_id)),
            sources_discovered=int(item["sources_discovered"] or 0),
            sources_processed=int(item["sources_processed_display"]),
            **_phase_flags(phase_flags_by_run, run_id),
        )
        enriched.append(item)
    return enriched


def cost_per_call(cost_usd: float, call_count: int) -> float | None:
    if call_count <= 0:
        return None
    return cost_usd / call_count


def get_cost_breakdown(
    store: SQLiteStore,
    persona_id: str,
    *,
    group_by: str = "provider",
    run_id: int | None = None,
    days: int = 30,
    provider: str | None = None,
    exclude_provider: str | None = None,
) -> list[dict[str, Any]]:
    group_columns = {
        "provider": "provider",
        "model": "model",
        "operation": "operation",
        "day": "date(created_at)",
    }
    if group_by not in group_columns:
        raise ValueError(f"Unsupported group_by: {group_by}")
    column = group_columns[group_by]
    query = f"""
        SELECT
            {column} AS label,
            COALESCE(SUM(cost_usd), 0) AS cost_usd,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(api_credits), 0) AS api_credits,
            COUNT(*) AS call_count
        FROM api_usage_logs
        WHERE persona_id = ?
    """
    params: list[Any] = [persona_id]
    if run_id is not None:
        query += " AND run_id = ?"
        params.append(run_id)
    if days > 0:
        query += " AND date(created_at) >= date('now', ?)"
        params.append(f"-{days - 1} days")
    if provider is not None:
        query += " AND provider = ?"
        params.append(provider)
    if exclude_provider is not None:
        query += " AND provider != ?"
        params.append(exclude_provider)
    query += f" GROUP BY {column} ORDER BY cost_usd DESC"
    rows = store.connect().execute(query, params).fetchall()
    return [
        {
            "label": str(row["label"] or "unknown"),
            "cost_usd": float(row["cost_usd"]),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "api_credits": float(row["api_credits"]),
            "call_count": int(row["call_count"]),
        }
        for row in rows
    ]
