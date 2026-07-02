from __future__ import annotations

DEFAULT_GEMINI_TIMEOUT_MS = 180_000
"""Default per-request timeout for Gemini API calls, in milliseconds.

The google-genai SDK has no timeout by default, so a stalled connection
(bad proxy, dead network, etc.) hangs forever instead of raising an error
that our retry/fallback logic could handle. Without this, a single stuck
source blocks the whole pipeline run indefinitely.
"""


def build_gemini_client(api_key: str, *, timeout_ms: int = DEFAULT_GEMINI_TIMEOUT_MS):
    from google import genai
    from google.genai import types

    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))
