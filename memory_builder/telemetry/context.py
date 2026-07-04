from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

from memory_builder.pipeline.fatal_errors import PipelineCancelledError, PipelineFatalError
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.pricing import (
    estimate_gemini_cost_usd,
    estimate_openai_embedding_cost_usd,
    estimate_scrapfly_cost_usd,
)
from memory_builder.telemetry.run_watchdog import HEARTBEAT_INTERVAL_SECONDS


log = logging.getLogger(__name__)

_current_run: ContextVar["PipelineRunContext | None"] = ContextVar("pipeline_run_context", default=None)


@dataclass
class PipelineRunContext:
    persona_id: str
    run_id: int
    store: SQLiteStore
    run_options: dict[str, Any] = field(default_factory=dict)
    current_source_id: int | None = field(default=None, init=False)
    current_source_url: str = field(default="", init=False)
    current_source_title: str = field(default="", init=False)
    current_source_type: str = field(default="", init=False)
    current_channel_url: str = field(default="", init=False)
    current_platform: str = field(default="", init=False)

    def bind_source(
        self,
        *,
        source_id: int,
        source_url: str,
        source_title: str = "",
        source_type: str = "",
        channel_url: str | None = None,
    ) -> None:
        from memory_builder.telemetry.source_labels import platform_label

        self.current_source_id = source_id
        self.current_source_url = source_url
        self.current_source_title = source_title
        self.current_source_type = source_type
        self.current_channel_url = channel_url or ""
        self.current_platform = platform_label(
            source_type,
            source_url,
            channel_url=self.current_channel_url,
        )

    def clear_source(self) -> None:
        self.current_source_id = None
        self.current_source_url = ""
        self.current_source_title = ""
        self.current_source_type = ""
        self.current_channel_url = ""
        self.current_platform = ""

    def _event_metadata(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        merged: dict[str, Any] = dict(metadata or {})
        if self.current_source_id is None:
            return merged
        merged.setdefault("source_type", self.current_source_type)
        merged.setdefault("source_url", self.current_source_url)
        merged.setdefault("title", self.current_source_title)
        merged.setdefault("platform", self.current_platform)
        return merged

    def event(
        self,
        stage: str,
        message: str,
        *,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        event_id = self.store.log_pipeline_event(
            persona_id=self.persona_id,
            run_id=self.run_id,
            stage=stage,
            message=message,
            source_id=source_id if source_id is not None else self.current_source_id,
            metadata=self._event_metadata(metadata),
        )
        log.info("[run=%s stage=%s] %s", self.run_id, stage, message)
        return event_id

    def record_api_usage(
        self,
        *,
        provider: str,
        operation: str,
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        api_credits: float = 0.0,
        cost_usd: float | None = None,
        is_estimated: bool = True,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        if cost_usd is None:
            cost_usd = 0.0
        row_id = self.store.log_api_usage(
            persona_id=self.persona_id,
            run_id=self.run_id,
            source_id=source_id if source_id is not None else self.current_source_id,
            provider=provider,
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_credits=api_credits,
            cost_usd=cost_usd,
            is_estimated=is_estimated,
            metadata=metadata or {},
        )
        return row_id

    def record_gemini(
        self,
        *,
        response: Any,
        operation: str,
        model: str,
        input_modality: str = "text",
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from memory_builder.telemetry.usage_helpers import gemini_usage_tokens

        input_tokens, output_tokens = gemini_usage_tokens(response)
        estimated = input_tokens == 0 and output_tokens == 0
        cost = estimate_gemini_cost_usd(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_modality=input_modality,
        )
        self.record_api_usage(
            provider="google",
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            is_estimated=estimated,
            source_id=source_id,
            metadata={**(metadata or {}), "input_modality": input_modality},
        )

    def record_openai_embedding(
        self,
        *,
        model: str,
        input_tokens: int,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cost = estimate_openai_embedding_cost_usd(model=model, input_tokens=input_tokens)
        self.record_api_usage(
            provider="openai",
            operation="embedding",
            model=model,
            input_tokens=input_tokens,
            cost_usd=cost,
            is_estimated=False,
            source_id=source_id,
            metadata=metadata or {},
        )

    def record_scrapfly(
        self,
        *,
        result: Any,
        operation: str,
        source_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from memory_builder.telemetry.usage_helpers import scrapfly_api_credits

        credits = scrapfly_api_credits(result)
        cost = estimate_scrapfly_cost_usd(credits=credits) if credits else 0.0
        self.record_api_usage(
            provider="scrapfly",
            operation=operation,
            api_credits=credits,
            cost_usd=cost,
            is_estimated=credits == 0,
            source_id=source_id,
            metadata=metadata or {},
        )


def get_run_context() -> PipelineRunContext | None:
    return _current_run.get()


@contextmanager
def run_context(ctx: PipelineRunContext) -> Iterator[PipelineRunContext]:
    token = _current_run.set(ctx)
    stop_heartbeat = threading.Event()

    def heartbeat_loop() -> None:
        while not stop_heartbeat.wait(timeout=HEARTBEAT_INTERVAL_SECONDS):
            try:
                ctx.store.touch_run_activity(ctx.run_id)
            except Exception:
                log.exception("Run heartbeat failed for run=%s", ctx.run_id)

    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        name=f"run-heartbeat-{ctx.run_id}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        ctx.event(
            "run_started",
            f"Pipeline run {ctx.run_id} started",
            metadata=ctx.run_options,
        )
        yield ctx
        ctx.event("run_finished", f"Pipeline run {ctx.run_id} finished")
    except (PipelineFatalError, PipelineCancelledError):
        raise
    except BaseException:
        ctx.store.mark_run_interrupted(ctx.run_id)
        raise
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
        _current_run.reset(token)
