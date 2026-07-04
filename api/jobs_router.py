from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.jobs import job_manager
from api.schemas import JobCreateRequest, JobItem

router = APIRouter(tags=["jobs"])


def _job_item(record) -> JobItem:
    return JobItem(
        job_id=record.job_id,
        persona_id=record.persona_id,
        command=record.command,
        status=record.status,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        exit_code=record.exit_code,
        log_tail=record.log_lines[-50:],
    )


@router.get("/jobs", response_model=list[JobItem])
def list_jobs() -> list[JobItem]:
    return [_job_item(record) for record in job_manager.list_jobs()]


@router.get("/jobs/{job_id}", response_model=JobItem)
def get_job(job_id: str) -> JobItem:
    record = job_manager.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_item(record)


@router.post("/jobs", response_model=JobItem)
def create_job(body: JobCreateRequest) -> JobItem:
    script = "memory_sync.py" if body.kind == "sync" else "memory_build.py"
    args = ["--persona", body.persona_id]
    if body.only_platform:
        args.extend(["--only", body.only_platform])
    if body.limit is not None:
        args.extend(["--limit", str(body.limit)])
    if body.retry_failed:
        args.append("--retry-failed")
    if body.skip_discovery:
        args.append("--skip-discovery")
    if body.dry_run:
        args.append("--dry-run")
    if body.discover_only:
        args.append("--discover-only")
    if body.discovery_limit is not None:
        args.extend(["--discovery-limit", str(body.discovery_limit)])
    record = job_manager.start(persona_id=body.persona_id, script=script, args=args)
    return _job_item(record)


@router.delete("/jobs/{job_id}", response_model=JobItem)
def stop_job(job_id: str) -> JobItem:
    try:
        record = job_manager.stop_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return _job_item(record)
