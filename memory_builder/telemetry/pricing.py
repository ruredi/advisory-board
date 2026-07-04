from __future__ import annotations

import os


# USD per 1M tokens (Gemini Standard tier, 2026-07). Estimates only.
GEMINI_INPUT_USD_PER_M: dict[str, float] = {
    "text": 0.30,
    "audio": 1.00,
    "image": 0.30,
}
GEMINI_OUTPUT_USD_PER_M = 2.50

OPENAI_EMBEDDING_USD_PER_M: dict[str, float] = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
    "text-embedding-ada-002": 0.10,
}

# GPT-4o chat vision rough Standard tier (USD per 1M tokens).
OPENAI_VISION_INPUT_USD_PER_M = 2.50
OPENAI_VISION_OUTPUT_USD_PER_M = 10.00

DEFAULT_SCRAPFLY_USD_PER_CREDIT = 30.0 / 200_000  # Discovery plan baseline


def scrapfly_usd_per_credit() -> float:
    raw = os.environ.get("SCRAPFLY_USD_PER_CREDIT", "").strip()
    if raw:
        return float(raw)
    return DEFAULT_SCRAPFLY_USD_PER_CREDIT


def estimate_gemini_cost_usd(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    input_modality: str = "text",
) -> float:
    del model  # same tier pricing for flash family in our usage
    input_rate = GEMINI_INPUT_USD_PER_M.get(input_modality, GEMINI_INPUT_USD_PER_M["text"])
    return (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * GEMINI_OUTPUT_USD_PER_M


def estimate_openai_embedding_cost_usd(*, model: str, input_tokens: int) -> float:
    rate = OPENAI_EMBEDDING_USD_PER_M.get(model, 0.02)
    return (input_tokens / 1_000_000) * rate


def estimate_openai_vision_cost_usd(*, model: str, input_tokens: int, output_tokens: int) -> float:
    del model
    return (input_tokens / 1_000_000) * OPENAI_VISION_INPUT_USD_PER_M + (
        output_tokens / 1_000_000
    ) * OPENAI_VISION_OUTPUT_USD_PER_M


def estimate_scrapfly_cost_usd(*, credits: float) -> float:
    return credits * scrapfly_usd_per_credit()


DEFAULT_SUPADATA_USD_PER_CREDIT = 30.0 / 2000  # rough Discovery-tier baseline


def supadata_usd_per_credit() -> float:
    raw = os.environ.get("SUPADATA_USD_PER_CREDIT", "").strip()
    if raw:
        return float(raw)
    return DEFAULT_SUPADATA_USD_PER_CREDIT


def estimate_supadata_cost_usd(*, credits: float) -> float:
    return credits * supadata_usd_per_credit()
