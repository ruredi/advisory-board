from __future__ import annotations

from typing import Any


def gemini_usage_tokens(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return 0, 0
    prompt = getattr(usage, "prompt_token_count", None) or getattr(usage, "input_token_count", None) or 0
    output = (
        getattr(usage, "candidates_token_count", None)
        or getattr(usage, "output_token_count", None)
        or 0
    )
    return int(prompt), int(output)


def scrapfly_api_credits(result: Any) -> float:
    for attr in ("cost", "api_cost", "total_cost"):
        value = getattr(result, attr, None)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    scrape_result = getattr(result, "scrape_result", None) or getattr(result, "result", None)
    if isinstance(scrape_result, dict):
        context = scrape_result.get("context") or {}
        cost = context.get("cost")
        if cost is not None:
            try:
                return float(cost)
            except (TypeError, ValueError):
                pass
    return 0.0


def maybe_record_scrapfly(result: Any, *, operation: str, metadata: dict | None = None) -> None:
    from memory_builder.telemetry.context import get_run_context

    ctx = get_run_context()
    if ctx:
        ctx.record_scrapfly(result=result, operation=operation, metadata=metadata)
