from __future__ import annotations

import json
import os
from typing import Any

from scrapfly import ScrapflyClient

from memory_builder.env import load_project_env


def get_scrapfly_key() -> str:
    load_project_env()
    key = os.environ.get("SCRAPFLY_KEY", "").strip() or os.environ.get("SCRAPFLY_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SCRAPFLY_KEY environment variable is required for social media scraping. "
            "Set it in advisory-board/.env (copied from secret-project) or export it. "
            "Dashboard: https://scrapfly.io/dashboard"
        )
    return key


def get_scrapfly_client() -> ScrapflyClient:
    return ScrapflyClient(key=get_scrapfly_key())


def scrapfly_failure_message(result: Any) -> str | None:
    scrape_result = getattr(result, "scrape_result", None) or {}
    if not isinstance(scrape_result, dict):
        scrape_result = {}
    error = scrape_result.get("error")
    if isinstance(error, dict):
        code = str(error.get("code") or "")
        message = str(error.get("message") or "").strip()
        if code == "ERR::SCRAPE::QUOTA_LIMIT_REACHED":
            return "Scrapfly kvóta elfogyott — bővítsd a csomagot vagy várj a havi resetre."
        if message:
            return f"Scrapfly hiba ({code}): {message.rstrip(' -')}"
    status = getattr(result, "status_code", None) or scrape_result.get("status_code")
    content = getattr(result, "content", None) or scrape_result.get("content") or ""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    if not str(content).strip():
        if status == 429:
            return "Scrapfly rate limit (429) — próbáld később, vagy ellenőrizd a kvótát."
        if status and int(status) >= 400:
            return f"Scrapfly scrape sikertelen (HTTP {status}), üres válasz."
    return None


def parse_scrapfly_json(result: Any, *, operation: str) -> Any:
    failure = scrapfly_failure_message(result)
    if failure:
        raise RuntimeError(failure)
    content = getattr(result, "content", None) or ""
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    if not str(content).strip():
        status = getattr(result, "status_code", "?")
        raise RuntimeError(
            f"Üres scrape válasz ({operation}, HTTP {status}). Ellenőrizd a SCRAPFLY_KEY kvótát."
        )
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        status = getattr(result, "status_code", "?")
        preview = str(content)[:120].replace("\n", " ")
        raise RuntimeError(
            f"Nem JSON scrape válasz ({operation}, HTTP {status}): {preview}"
        ) from exc
