from __future__ import annotations

import subprocess
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class JobRecord:
    job_id: str
    persona_id: str
    command: list[str]
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    _process: subprocess.Popen[str] | None = field(default=None, repr=False)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def start(
        self,
        *,
        persona_id: str,
        script: str,
        args: list[str],
    ) -> JobRecord:
        command = [str(ROOT / ".venv" / "bin" / "python3"), str(ROOT / "scripts" / script), *args]
        job_id = uuid.uuid4().hex[:12]
        record = JobRecord(
            job_id=job_id,
            persona_id=persona_id,
            command=command,
            status="running",
            created_at=datetime.now(timezone.utc).isoformat(),
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        record._process = process
        with self._lock:
            self._jobs[job_id] = record
        thread = threading.Thread(target=self._watch, args=(job_id,), daemon=True)
        thread.start()
        return record

    def _watch(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            process = record._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            with self._lock:
                record.log_lines.append(line.rstrip())
                if len(record.log_lines) > 500:
                    record.log_lines = record.log_lines[-500:]
        exit_code = process.wait()
        with self._lock:
            record.exit_code = exit_code
            record.status = "succeeded" if exit_code == 0 else "failed"
            record.finished_at = datetime.now(timezone.utc).isoformat()
            record._process = None

    def list_jobs(self) -> list[JobRecord]:
        with self._lock:
            return list(self._jobs.values())

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def stop_job(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise KeyError(job_id)
            process = record._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        with self._lock:
            if record.status == "running":
                record.status = "stopped"
                record.finished_at = datetime.now(timezone.utc).isoformat()
                record.exit_code = record._process.returncode if record._process else -1
                record._process = None
            return record


job_manager = JobManager()
