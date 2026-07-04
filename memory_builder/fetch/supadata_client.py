"""Supadata transcript API — social video URL → plain text."""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from memory_builder.env import load_project_env


log = logging.getLogger(__name__)

SUPADATA_BASE_URL = "https://api.supadata.ai/v1"
DEFAULT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_MAX_POLL_SECONDS = 600.0
X_STATUS_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:x|twitter)\.com/[^/?#]+/status/(\d{10,25})",
    re.IGNORECASE,
)


def get_supadata_key() -> str:
    import os

    load_project_env()
    key = os.environ.get("SUPADATA_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SUPADATA_API_KEY is required for social video transcription. "
            "Set it in advisory-board/.env (copied from secret-project)."
        )
    return key


def normalize_supadata_url(url: str) -> str:
    """Strip X /video/N suffix so Supadata receives a canonical status URL."""
    match = X_STATUS_URL_PATTERN.search(url)
    if match:
        return match.group(0)
    return url.split("?")[0].rstrip("/")


def _parse_billable_credits(response: httpx.Response) -> float:
    raw = response.headers.get("x-billable-requests", "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _record_supadata_usage(*, credits: float, operation: str, metadata: dict[str, Any]) -> None:
    from memory_builder.telemetry.context import get_run_context
    from memory_builder.telemetry.pricing import estimate_supadata_cost_usd

    ctx = get_run_context()
    if not ctx:
        return
    ctx.record_api_usage(
        provider="supadata",
        operation=operation,
        api_credits=credits,
        cost_usd=estimate_supadata_cost_usd(credits=credits) if credits else 0.0,
        is_estimated=credits == 0,
        metadata=metadata,
    )


def _extract_transcript_text(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for chunk in content:
            if isinstance(chunk, dict):
                text = str(chunk.get("text") or "").strip()
                if text:
                    parts.append(text)
            elif isinstance(chunk, str) and chunk.strip():
                parts.append(chunk.strip())
        return "\n".join(parts).strip()
    result = payload.get("result")
    if isinstance(result, dict):
        return _extract_transcript_text(result)
    return ""


def _request_transcript(
    client: httpx.Client,
    *,
    api_key: str,
    url: str,
    lang: str | None,
    mode: str,
) -> httpx.Response:
    params: dict[str, str | bool] = {"url": url, "text": True, "mode": mode}
    if lang:
        params["lang"] = lang
    return client.get(
        f"{SUPADATA_BASE_URL}/transcript",
        params=params,
        headers={"x-api-key": api_key},
    )


def fetch_transcript(
    url: str,
    *,
    lang: str | None = None,
    mode: str = "auto",
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_poll_seconds: float = DEFAULT_MAX_POLL_SECONDS,
) -> str:
    """Fetch plain-text transcript for a supported social video URL."""
    api_key = get_supadata_key()
    normalized = normalize_supadata_url(url)
    metadata = {"url": normalized, "mode": mode}

    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        response = _request_transcript(client, api_key=api_key, url=normalized, lang=lang, mode=mode)
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"Supadata transcript failed ({response.status_code}): {detail}")

        payload = response.json()
        _record_supadata_usage(
            credits=_parse_billable_credits(response),
            operation="transcript",
            metadata=metadata,
        )

        if response.status_code == 202 or payload.get("jobId"):
            job_id = str(payload.get("jobId") or "")
            if not job_id:
                raise RuntimeError("Supadata returned async response without jobId")
            return _poll_transcript_job(
                client,
                api_key=api_key,
                job_id=job_id,
                poll_interval_seconds=poll_interval_seconds,
                max_poll_seconds=max_poll_seconds,
                metadata=metadata,
            )

        text = _extract_transcript_text(payload)
        if not text:
            raise RuntimeError(f"Supadata returned empty transcript for {normalized}")
        return text


def _poll_transcript_job(
    client: httpx.Client,
    *,
    api_key: str,
    job_id: str,
    poll_interval_seconds: float,
    max_poll_seconds: float,
    metadata: dict[str, Any],
) -> str:
    deadline = time.monotonic() + max_poll_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"{SUPADATA_BASE_URL}/transcript/{quote(job_id, safe='')}",
            headers={"x-api-key": api_key},
        )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"Supadata job poll failed ({response.status_code}): {detail}")
        payload = response.json()
        status = str(payload.get("status") or "").lower()
        if status == "completed":
            _record_supadata_usage(
                credits=_parse_billable_credits(response),
                operation="transcript_job",
                metadata={**metadata, "job_id": job_id},
            )
            text = _extract_transcript_text(payload)
            if not text:
                raise RuntimeError(f"Supadata job {job_id} completed with empty transcript")
            return text
        if status == "failed":
            error = payload.get("error") or payload.get("message") or "unknown error"
            raise RuntimeError(f"Supadata transcript job failed: {error}")
        time.sleep(poll_interval_seconds)
    raise RuntimeError(f"Supadata transcript job timed out after {max_poll_seconds:.0f}s: {job_id}")
