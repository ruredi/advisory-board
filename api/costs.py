from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.deps import persona_store
from api.schemas import (
    CostBreakdownItem,
    CostSummary,
    PipelineEvent,
    ScrapflyCostSummary,
    ScrapflyDailyUsage,
    ScrapflySubscription,
)
from memory_builder.fetch.scrapfly_account import fetch_scrapfly_subscription
from memory_builder.telemetry.queries import (
    cost_per_call,
    get_cost_breakdown,
    get_cost_totals,
    list_pipeline_events,
)

router = APIRouter(tags=["costs"])


@router.get("/costs/scrapfly/subscription", response_model=ScrapflySubscription)
def scrapfly_subscription() -> ScrapflySubscription:
    try:
        info = fetch_scrapfly_subscription()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scrapfly account API hiba: {exc}") from exc
    return ScrapflySubscription(
        plan_name=info.plan_name,
        period_start=info.period_start,
        period_end=info.period_end,
        credits_used=info.credits_used,
        credits_limit=info.credits_limit,
        credits_remaining=info.credits_remaining,
        plan_price_usd=info.plan_price_usd,
        usage_usd=info.usage_usd,
        usd_per_credit=info.usd_per_credit,
        quota_reached=info.quota_reached,
        concurrent_usage=info.concurrent_usage,
        concurrent_limit=info.concurrent_limit,
        project_name=info.project_name,
    )


@router.get("/personas/{persona_id}/costs/summary", response_model=CostSummary)
def cost_summary(persona_id: str) -> CostSummary:
    with persona_store(persona_id) as store:
        today = get_cost_totals(store, persona_id, day="now")
        total = get_cost_totals(store, persona_id)
        today_api = get_cost_totals(store, persona_id, day="now", exclude_provider="scrapfly")
        today_scrapfly = get_cost_totals(store, persona_id, day="now", provider="scrapfly")
    return CostSummary(
        today_usd=today.cost_usd,
        today_calls=today.call_count,
        total_usd=total.cost_usd,
        total_calls=total.call_count,
        today_api_usd=today_api.cost_usd,
        today_api_calls=today_api.call_count,
        today_scrapfly_usd=today_scrapfly.cost_usd,
        today_scrapfly_calls=today_scrapfly.call_count,
        today_scrapfly_credits=today_scrapfly.api_credits,
    )


@router.get("/personas/{persona_id}/costs/scrapfly", response_model=ScrapflyCostSummary)
def scrapfly_cost_summary(
    persona_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> ScrapflyCostSummary:
    with persona_store(persona_id) as store:
        today = get_cost_totals(store, persona_id, day="now", provider="scrapfly")
        total = get_cost_totals(store, persona_id, provider="scrapfly")
        daily_rows = get_cost_breakdown(
            store,
            persona_id,
            group_by="day",
            days=days,
            provider="scrapfly",
        )
        operation_rows = get_cost_breakdown(
            store,
            persona_id,
            group_by="operation",
            days=days,
            provider="scrapfly",
        )
    return ScrapflyCostSummary(
        today_usd=today.cost_usd,
        today_credits=today.api_credits,
        today_calls=today.call_count,
        today_cost_per_scrape=cost_per_call(today.cost_usd, today.call_count),
        total_usd=total.cost_usd,
        total_credits=total.api_credits,
        total_calls=total.call_count,
        total_cost_per_scrape=cost_per_call(total.cost_usd, total.call_count),
        daily=[
            ScrapflyDailyUsage(
                day=row["label"],
                cost_usd=row["cost_usd"],
                api_credits=row["api_credits"],
                call_count=row["call_count"],
            )
            for row in sorted(daily_rows, key=lambda item: item["label"])
        ],
        by_operation=[CostBreakdownItem(**row) for row in operation_rows],
    )


@router.get("/personas/{persona_id}/costs/breakdown", response_model=list[CostBreakdownItem])
def cost_breakdown(
    persona_id: str,
    group_by: str = Query(default="provider", pattern="^(provider|model|operation|day)$"),
    run_id: int | None = None,
    days: int = Query(default=30, ge=1, le=365),
    exclude_provider: str | None = Query(default=None),
) -> list[CostBreakdownItem]:
    with persona_store(persona_id) as store:
        rows = get_cost_breakdown(
            store,
            persona_id,
            group_by=group_by,
            run_id=run_id,
            days=days,
            exclude_provider=exclude_provider,
        )
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
