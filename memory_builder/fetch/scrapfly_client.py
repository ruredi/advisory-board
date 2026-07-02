from __future__ import annotations

import os

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
