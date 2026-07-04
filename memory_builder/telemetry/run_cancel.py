from __future__ import annotations

import logging
import os
import re
import signal
import subprocess

from memory_builder.pipeline.fatal_errors import PipelineCancelledError
from memory_builder.storage.sqlite_store import STOP_REASON_INTERRUPTED, SQLiteStore

log = logging.getLogger(__name__)

_PIPELINE_CMD = re.compile(r"memory_(?:build|sync)\.py.*--persona\s+(\S+)")


def signal_run_process(pid: int) -> bool:
    """Send SIGTERM to a pipeline process. Returns True if the signal was sent."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        log.warning("No permission to signal pipeline pid=%s", pid)
        return False


def find_pipeline_pid(persona_id: str) -> int | None:
    try:
        result = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    for line in result.stdout.splitlines():
        match = _PIPELINE_CMD.search(line)
        if match and match.group(1) == persona_id:
            pid_text = line.strip().split(None, 1)[0]
            try:
                return int(pid_text)
            except ValueError:
                continue
    return None


def abort_if_run_cancelled(
    store: SQLiteStore,
    run_id: int,
    *,
    summary: dict[str, int | str] | None = None,
) -> None:
    if not store.is_run_cancel_requested(run_id):
        return
    store.mark_run_stopped(
        run_id,
        reason=STOP_REASON_INTERRUPTED,
        event_stage="run_interrupted",
        message=f"Pipeline run {run_id} stopped by user request",
        summary=summary,
    )
    raise PipelineCancelledError(f"Run {run_id} cancelled")


def stop_open_run(
    store: SQLiteStore,
    persona_id: str,
    run_id: int,
    *,
    job_manager=None,
) -> bool:
    """Request cancellation for a running sync run and signal its process if known."""
    row = store.connect().execute(
        """
        SELECT finished_at, pid FROM sync_runs
        WHERE id = ? AND persona_id = ?
        """,
        (run_id, persona_id),
    ).fetchone()
    if row is None or row["finished_at"] is not None:
        return False

    store.request_run_cancel(run_id)
    pid = int(row["pid"]) if row["pid"] is not None else None
    if pid is None:
        pid = find_pipeline_pid(persona_id)
    if pid is not None:
        signal_run_process(pid)

    if job_manager is not None:
        for record in job_manager.list_jobs():
            if record.persona_id == persona_id and record.status == "running":
                try:
                    job_manager.stop_job(record.job_id)
                except KeyError:
                    pass
                break

    return True
