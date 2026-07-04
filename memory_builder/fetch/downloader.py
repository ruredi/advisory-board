from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import httpx

from memory_builder.models import ProcessedDocument, SourceNature
from memory_builder.paths import sources_raw_dir
from memory_builder.storage.sqlite_store import text_hash


def source_slug(source_url: str) -> str:
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:16]
    return digest


def fetch_url(url: str, timeout: float = 60.0) -> tuple[bytes, dict[str, str]]:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    headers = {key.lower(): value for key, value in response.headers.items()}
    return response.content, headers


def save_raw_bytes(persona_id: str, source_url: str, suffix: str, content: bytes, root: Path | None = None) -> Path:
    from memory_builder.paths import project_root

    base = sources_raw_dir(persona_id, root or project_root()) / source_slug(source_url)
    base.mkdir(parents=True, exist_ok=True)
    path = base / suffix
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def save_json_metadata(persona_id: str, source_url: str, metadata: dict, root: Path | None = None) -> Path:
    from memory_builder.paths import project_root

    base = sources_raw_dir(persona_id, root or project_root()) / source_slug(source_url)
    base.mkdir(parents=True, exist_ok=True)
    path = base / "metadata.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
