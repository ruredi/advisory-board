from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Iterable

import httpx
import numpy as np

from memory_builder.pipeline.fatal_errors import is_transient_error
from memory_builder.telemetry.context import get_run_context

log = logging.getLogger(__name__)

MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}
HASH_EMBED_DIMENSIONS = 384
# OpenAI embeddings accept up to 8192 tokens; ~24k chars is a safe upper bound.
MAX_EMBEDDING_INPUT_CHARS = 24_000


def truncate_embedding_input(text: str, max_chars: int = MAX_EMBEDDING_INPUT_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    break_at = truncated.rfind("\n")
    if break_at < max_chars // 2:
        break_at = truncated.rfind(" ")
    if break_at > 0:
        truncated = truncated[:break_at]
    return truncated.strip()


def embedding_dimensions(model: str, *, use_api: bool) -> int:
    if use_api:
        return MODEL_DIMENSIONS.get(model, 1536)
    return HASH_EMBED_DIMENSIONS


def _hash_embed(text: str, dimensions: int = HASH_EMBED_DIMENSIONS) -> list[float]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    vector = np.zeros(dimensions, dtype=np.float32)
    if not tokens:
        return vector.tolist()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(dimensions):
            vector[i] += (digest[i % len(digest)] / 255.0) - 0.5
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.astype(np.float32).tolist()


class EmbeddingClient:
    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    @property
    def uses_api(self) -> bool:
        return bool(self.api_key)

    @property
    def dimensions(self) -> int:
        return embedding_dimensions(self.model, use_api=self.uses_api)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        items = [truncate_embedding_input(text) for text in texts if text.strip()]
        if not items:
            return []
        if not self.api_key:
            return [_hash_embed(text, self.dimensions) for text in items]
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._embed_via_api(items)
            except Exception as exc:
                last_error = exc
                if attempt < 2 and is_transient_error(exc):
                    time.sleep(5 * (attempt + 1))
                    continue
                break
        if last_error is not None:
            log.warning(
                "OpenAI embedding failed after retries (%s); using hash fallback for %s texts",
                last_error,
                len(items),
            )
        return [_hash_embed(text, self.dimensions) for text in items]

    def _embed_via_api(self, items: list[str]) -> list[list[float]]:
        response = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": items},
            timeout=120.0,
        )
        if response.is_error:
            detail = response.text.strip()
            raise httpx.HTTPStatusError(
                f"{response.status_code} {response.reason_phrase} from OpenAI embeddings: {detail}",
                request=response.request,
                response=response,
            )
        payload = response.json()
        data = payload["data"]
        ordered = sorted(data, key=lambda row: row["index"])
        ctx = get_run_context()
        if ctx:
            usage = payload.get("usage") or {}
            total_tokens = int(usage.get("total_tokens") or usage.get("prompt_tokens") or 0)
            ctx.record_openai_embedding(
                model=self.model,
                input_tokens=total_tokens,
                metadata={"batch_size": len(items)},
            )
        return [row["embedding"] for row in ordered]
