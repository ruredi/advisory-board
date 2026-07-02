from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import persona_store
from api.schemas import PipelineEvent, RunProgressResponse, SyncRunDetail
from memory_builder.telemetry.queries import (
    get_run_progress,
    list_pipeline_events,
    list_sync_runs,
)

router = APIRouter(tags=["runs"])


@router.get("/personas/{persona_id}/runs", response_model=list[SyncRunDetail])
def list_runs(persona_id: str, limit: int = 50) -> list[SyncRunDetail]:
    with persona_store(persona_id) as store:
        rows = list_sync_runs(store, persona_id, limit=limit)
    return [
        SyncRunDetail(
            run_id=int(row["id"]),
            persona_id=str(row["persona_id"]),
            started_at=str(row["started_at"]),
            finished_at=row["finished_at"],
            sources_discovered=int(row["sources_discovered"] or 0),
            sources_processed=int(row.get("sources_processed_display", row["sources_processed"] or 0)),
            units_created=int(row["units_created"] or 0),
            units_skipped_duplicate=int(row["units_skipped_duplicate"] or 0),
            errors=int(row.get("errors_display", row["errors"] or 0)),
            cost_usd=float(row.get("cost_usd_display", row["cost_usd"] or 0)),
            summary=row["summary"],
            status="running" if row["finished_at"] is None else "finished",
            done_count=int(row.get("done_count", 0)),
            error_count=int(row.get("error_count", 0)),
            skip_count=int(row.get("skip_count", 0)),
            api_calls=int(row.get("api_calls", 0)),
        )
        for row in rows
    ]


@router.get("/personas/{persona_id}/runs/{run_id}", response_model=RunProgressResponse)
def get_run(persona_id: str, run_id: int) -> RunProgressResponse:
    with persona_store(persona_id) as store:
        progress = get_run_progress(store, persona_id, run_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunProgressResponse(
        run_id=progress.run_id,
        persona_id=progress.persona_id,
        started_at=progress.started_at,
        finished_at=progress.finished_at,
        status="running" if progress.finished_at is None else "finished",
        latest_stage=progress.latest_stage,
        latest_message=progress.latest_message,
        events_count=progress.events_count,
        sources_processed=progress.sources_processed,
        cost_run_usd=progress.cost_run_usd,
        cost_persona_usd=progress.cost_persona_usd,
        cost_today_usd=progress.cost_today_usd,
        current_platform=progress.current_platform,
        current_title=progress.current_title,
        current_url=progress.current_url,
        current_stage=progress.current_stage,
        done_count=progress.done_count,
        error_count=progress.error_count,
        skip_count=progress.skip_count,
    )


@router.get("/personas/{persona_id}/runs/{run_id}/events", response_model=list[PipelineEvent])
def get_run_events(
    persona_id: str,
    run_id: int,
    after_id: int = 0,
    limit: int = 200,
) -> list[PipelineEvent]:
    with persona_store(persona_id) as store:
        events = list_pipeline_events(store, persona_id, run_id=run_id, after_id=after_id, limit=limit)
    return [PipelineEvent(**event) for event in events]


@router.get("/personas/{persona_id}/runs/{run_id}/events/stream")
async def stream_run_events(persona_id: str, run_id: int, after_id: int = 0):
    import asyncio
    import json

    async def event_generator():
        cursor = after_id
        while True:
            with persona_store(persona_id) as store:
                events = list_pipeline_events(
                    store, persona_id, run_id=run_id, after_id=cursor, limit=50
                )
                progress = get_run_progress(store, persona_id, run_id)
            for event in events:
                cursor = int(event["id"])
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            if progress and progress.finished_at is not None and not events:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
