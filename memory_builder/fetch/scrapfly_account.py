from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from memory_builder.fetch.scrapfly_client import get_scrapfly_key
from memory_builder.telemetry.pricing import estimate_scrapfly_cost_usd, scrapfly_usd_per_credit

SCRAPFLY_ACCOUNT_URL = "https://api.scrapfly.io/account"


@dataclass(frozen=True)
class ScrapflySubscriptionInfo:
    plan_name: str
    period_start: str
    period_end: str
    credits_used: int
    credits_limit: int
    credits_remaining: int
    plan_price_usd: float
    usage_usd: float
    usd_per_credit: float
    quota_reached: bool
    concurrent_usage: int
    concurrent_limit: int
    project_name: str


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_scrapfly_account_payload(payload: dict[str, Any]) -> ScrapflySubscriptionInfo:
    subscription = payload.get("subscription") or {}
    project = payload.get("project") or {}
    period = subscription.get("period") or {}
    usage = subscription.get("usage") or {}
    scrape = usage.get("scrape") or {}
    billing = subscription.get("billing") or {}
    plan_price = billing.get("plan_price") or {}
    credits_used = _as_int(scrape.get("current"))
    usd_per_credit = scrapfly_usd_per_credit()

    return ScrapflySubscriptionInfo(
        plan_name=str(subscription.get("plan_name") or "unknown"),
        period_start=str(period.get("start") or ""),
        period_end=str(period.get("end") or ""),
        credits_used=credits_used,
        credits_limit=_as_int(scrape.get("limit")),
        credits_remaining=_as_int(scrape.get("remaining")),
        plan_price_usd=_as_float(plan_price.get("amount")),
        usage_usd=estimate_scrapfly_cost_usd(credits=credits_used),
        usd_per_credit=usd_per_credit,
        quota_reached=bool(project.get("quota_reached")),
        concurrent_usage=_as_int(scrape.get("concurrent_usage")),
        concurrent_limit=_as_int(scrape.get("concurrent_limit")),
        project_name=str(project.get("name") or "default"),
    )


def fetch_scrapfly_subscription() -> ScrapflySubscriptionInfo:
    key = get_scrapfly_key()
    response = httpx.get(SCRAPFLY_ACCOUNT_URL, params={"key": key}, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Scrapfly account API váratlan választ adott.")
    return parse_scrapfly_account_payload(payload)
