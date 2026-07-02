from __future__ import annotations

from fastapi import APIRouter, Query

from api.deps import persona_store
from api.schemas import CostBreakdownItem, CostSummary, PipelineEvent
from memory_builder.telemetry.queries import get_cost_breakdown, get_cost_totals, list_pipeline_events

router = APIRouter(tags=["costs"])


@router.get("/personas/{persona_id}/costs/summary", response_model=CostSummary)
def cost_summary(persona_id: str) -> CostSummary:
    with persona_store(persona_id) as store:
        today = get_cost_totals(store, persona_id, day="now")
        total = get_cost_totals(store, persona_id)
    return CostSummary(
        today_usd=today.cost_usd,
        today_calls=today.call_count,
        total_usd=total.cost_usd,
        total_calls=total.call_count,
    )


@router.get("/personas/{persona_id}/costs/breakdown", response_model=list[CostBreakdownItem])
def cost_breakdown(
    persona_id: str,
    group_by: str = Query(default="provider", pattern="^(provider|model|operation|day)$"),
    run_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
) -> list[CostBreakdownItem]:
    with persona_store(persona_id) as store:
        rows = get_cost_breakdown(store, persona_id, group_by=group_by, run_id=run_id, days=days)
    return [CostBreakdownItem(**row) for row in rows]


@router.get("/personas/{persona_id}/logs", response_model=list[PipelineEvent])
def list_logs(
    persona_id: str,
    run_id: int | None = None,
    stage: str | None = None,
    after_id: int = 0,
    limit: int = Query(default=200, le=500),
) -> list[PipelineEvent]:
    with persona_store(persona_id) as store:
        events = list_pipeline_events(store, persona_id, run_id=run_id, after_id=after_id, limit=limit)
    if stage:
        events = [event for event in events if event["stage"] == stage]
    return [PipelineEvent(**event) for event in events]
