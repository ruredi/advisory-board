#!/usr/bin/env python3
"""Poll pipeline progress and API costs for GUI integration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.telemetry.queries import (
    get_cost_totals,
    get_pending_by_platform,
    get_run_activity,
    get_run_progress,
    get_source_display_map,
    list_pipeline_events,
)
from memory_builder.telemetry.source_labels import extract_stage_label, short_url
from memory_builder.storage.sqlite_store import SQLiteStore


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline run progress and cost snapshot.")
    parser.add_argument("--persona", default="hormozi", help="Persona id")
    parser.add_argument("--run-id", type=int, default=None, help="Sync run id (default: latest)")
    parser.add_argument("--after-event-id", type=int, default=0, help="Return events with id > this")
    parser.add_argument("--events-limit", type=int, default=50, help="Max events to return")
    parser.add_argument("--json", action="store_true", help="Output JSON for GUI polling")
    return parser.parse_args(argv)


def _latest_run_id(store: SQLiteStore, persona_id: str) -> int | None:
    row = store.connect().execute(
        """
        SELECT id FROM sync_runs
        WHERE persona_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (persona_id,),
    ).fetchone()
    return int(row["id"]) if row else None


def _format_event_line(event: dict, display_map: dict[int, dict[str, str]] | None = None) -> str:
    meta = event.get("metadata") or {}
    source_id = int(event["source_id"]) if event.get("source_id") else None
    display = display_map.get(source_id, {}) if display_map and source_id else {}
    site = str(meta.get("platform", "")) or display.get("platform", "")
    title = str(meta.get("title", "")) or display.get("title", "") or str(event.get("message", ""))
    stage = str(event.get("stage", ""))
    if stage == "discovery":
        by_type = meta.get("by_type") or {}
        if by_type:
            from memory_builder.telemetry.source_labels import TYPE_LABELS

            parts = ", ".join(
                f"{TYPE_LABELS.get(t, t)}={n}" for t, n in sorted(by_type.items(), key=lambda x: -x[1])
            )
            return f"discovery: {event.get('message', '')} ({parts})"
        return f"discovery: {event.get('message', '')}"
    if stage.startswith("source_"):
        prefix = f"[{site}] " if site else ""
        if stage == "source_done":
            units = meta.get("units_new")
            display_title = title.removeprefix("Indexed: ").strip()
            suffix = f" ({units} units)" if units is not None else ""
            return f"OK  {prefix}{display_title}{suffix}"
        if stage == "source_error":
            err = str(event.get("message", ""))
            if len(err) > 72:
                err = err[:69] + "..."
            display_title = display.get("title", "") or title
            if display_title.startswith(("429 ", "503 ", "500 ")):
                display_title = display.get("title", "source failed")
            return f"ERR {prefix}{display_title} — {err}"
        if stage == "source_skip":
            return f"SKIP {prefix}{title} — {event.get('message', '')}"
        return f"    {prefix}{title} — {extract_stage_label(stage, meta)}"
    return f"{stage}: {event.get('message', '')}"


def _print_watch_view(
    *,
    run_id: int,
    progress,
    activity,
    cost_run,
    cost_persona,
    cost_today,
    events: list[dict],
    display_map: dict[int, dict[str, str]],
) -> None:
    status = "FINISHED" if progress and progress.finished_at else "RUNNING"
    print(f"run={run_id}  {status}  |  cost ${cost_run.cost_usd:.4f}  (today ${cost_today.cost_usd:.4f}, total ${cost_persona.cost_usd:.4f})")
    print("-" * 72)

    if activity.current_platform or activity.current_title:
        print(f"NOW  [{activity.current_platform}]  {activity.current_title}")
        if activity.current_url:
            print(f"     {short_url(activity.current_url, max_len=68)}")
        print(f"     step: {activity.current_stage}")
    elif progress and progress.latest_stage == "discovery":
        print("NOW  discovery")
    elif status == "FINISHED":
        print("NOW  idle")
    else:
        print("NOW  waiting")

    print("-" * 72)
    print(
        f"run progress: done={activity.done_count}  error={activity.error_count}  skip={activity.skip_count}  "
        f"|  api_calls={cost_run.call_count}"
    )
    if activity.pending_by_platform:
        queue = "  ".join(f"{name}={count}" for name, count in activity.pending_by_platform.items())
        print(f"queue pending: {queue}")
    print("-" * 72)

    source_events = [event for event in events if str(event.get("stage", "")).startswith("source_") or event.get("stage") == "discovery"]
    tail = source_events[-12:]
    if tail:
        for event in tail:
            print(_format_event_line(event, display_map))
    else:
        print("(no source events yet)")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    store = SQLiteStore(args.persona, ROOT)
    store.initialize()
    run_id = args.run_id or _latest_run_id(store, args.persona)
    if run_id is None:
        print("No sync runs found.", file=sys.stderr)
        return 1

    progress = get_run_progress(store, args.persona, run_id)
    activity = get_run_activity(store, args.persona, run_id)
    events = list_pipeline_events(
        store,
        args.persona,
        run_id=run_id,
        after_id=args.after_event_id,
        limit=args.events_limit,
    )
    cost_run = get_cost_totals(store, args.persona, run_id=run_id)
    cost_persona = get_cost_totals(store, args.persona)
    cost_today = get_cost_totals(store, args.persona, day="now")
    pending_by_platform = get_pending_by_platform(store, args.persona)
    source_ids = [int(event["source_id"]) for event in events if event.get("source_id")]
    display_map = get_source_display_map(store, source_ids)

    payload = {
        "run_id": run_id,
        "progress": None if progress is None else {
            "started_at": progress.started_at,
            "finished_at": progress.finished_at,
            "latest_stage": progress.latest_stage,
            "latest_message": progress.latest_message,
            "events_count": progress.events_count,
            "sources_processed": progress.sources_processed,
            "cost_run_usd": progress.cost_run_usd,
            "cost_persona_usd": progress.cost_persona_usd,
            "cost_today_usd": progress.cost_today_usd,
            "current_platform": progress.current_platform,
            "current_title": progress.current_title,
            "current_url": progress.current_url,
            "current_stage": progress.current_stage,
            "done_count": progress.done_count,
            "error_count": progress.error_count,
            "skip_count": progress.skip_count,
        },
        "activity": {
            "current_platform": activity.current_platform,
            "current_title": activity.current_title,
            "current_url": activity.current_url,
            "current_stage": activity.current_stage,
            "done_count": activity.done_count,
            "error_count": activity.error_count,
            "skip_count": activity.skip_count,
            "pending_by_platform": activity.pending_by_platform,
        },
        "cost": {
            "run_usd": cost_run.cost_usd,
            "persona_total_usd": cost_persona.cost_usd,
            "today_usd": cost_today.cost_usd,
            "run_api_calls": cost_run.call_count,
        },
        "queue_pending_by_platform": pending_by_platform,
        "events": events,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_watch_view(
            run_id=run_id,
            progress=progress,
            activity=activity,
            cost_run=cost_run,
            cost_persona=cost_persona,
            cost_today=cost_today,
            events=events,
            display_map=display_map,
        )
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
