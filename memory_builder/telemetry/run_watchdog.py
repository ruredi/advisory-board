from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from memory_builder.paths import project_root
from memory_builder.storage.sqlite_store import SQLiteStore

log = logging.getLogger(__name__)

STALE_THRESHOLD_SECONDS = 120
HEARTBEAT_INTERVAL_SECONDS = 30


def _parse_sqlite_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "T" in text and "+" not in text[10:] and text.count("-") >= 2:
        try:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_run_status(row: dict[str, object]) -> str:
    if row.get("finished_at") is None:
        return "running"
    reason = row.get("stop_reason")
    if reason == "interrupted":
        return "interrupted"
    if reason == "fatal_error":
        return "aborted"
    return "finished"


def compute_active_duration_seconds(row: dict[str, object], *, now: datetime | None = None) -> int:
    started = _parse_sqlite_ts(str(row.get("started_at") or ""))
    if started is None:
        return 0
    end_raw = row.get("stopped_at") or row.get("finished_at")
    if end_raw:
        ended = _parse_sqlite_ts(str(end_raw))
    elif row.get("finished_at") is None:
        ended = now or datetime.now(timezone.utc)
    else:
        ended = _parse_sqlite_ts(str(row.get("last_activity_at") or "")) or (now or datetime.now(timezone.utc))
    if ended is None:
        return 0
    return max(0, int((ended - started).total_seconds()))


def close_open_runs_for_persona(
    store: SQLiteStore,
    persona_id: str,
    *,
    reason: str = "interrupted",
) -> list[int]:
    rows = store.connect().execute(
        """
        SELECT id FROM sync_runs
        WHERE persona_id = ? AND finished_at IS NULL
        ORDER BY id
        """,
        (persona_id,),
    ).fetchall()
    closed: list[int] = []
    for row in rows:
        run_id = int(row["id"])
        if store.mark_run_interrupted(run_id, reason=reason):
            closed.append(run_id)
    if closed:
        log.info("Closed open runs for %s: %s", persona_id, closed)
    return closed


def close_stale_runs_for_persona(
    store: SQLiteStore,
    persona_id: str,
    *,
    threshold_seconds: int = STALE_THRESHOLD_SECONDS,
) -> list[int]:
    rows = store.connect().execute(
        """
        SELECT id FROM sync_runs
        WHERE persona_id = ?
          AND finished_at IS NULL
          AND datetime(COALESCE(last_activity_at, started_at)) < datetime('now', ?)
        ORDER BY id
        """,
        (persona_id, f"-{threshold_seconds} seconds"),
    ).fetchall()
    closed: list[int] = []
    for row in rows:
        run_id = int(row["id"])
        if store.mark_run_interrupted(run_id, reason="interrupted"):
            closed.append(run_id)
    if closed:
        log.info("Marked stale runs interrupted for %s: %s", persona_id, closed)
    return closed


def scan_all_stale_runs(
    root: Path | None = None,
    *,
    threshold_seconds: int = STALE_THRESHOLD_SECONDS,
) -> list[tuple[str, int]]:
    root = root or project_root()
    personas_dir = root / "memory_builder" / "config" / "personas"
    if not personas_dir.is_dir():
        return []
    closed: list[tuple[str, int]] = []
    for persona_path in sorted(personas_dir.glob("*.yaml")):
        persona_id = persona_path.stem
        store = SQLiteStore(persona_id, root)
        store.initialize()
        try:
            for run_id in close_stale_runs_for_persona(
                store,
                persona_id,
                threshold_seconds=threshold_seconds,
            ):
                closed.append((persona_id, run_id))
        finally:
            store.close()
    return closed
