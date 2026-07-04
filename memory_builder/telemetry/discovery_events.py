from __future__ import annotations

from typing import Any

from memory_builder.telemetry.context import get_run_context


def discovery_log(message: str, *, metadata: dict[str, Any] | None = None) -> None:
    print(f"discovery: {message}", flush=True)
    ctx = get_run_context()
    if ctx:
        ctx.event("discovery", message, metadata=metadata)
