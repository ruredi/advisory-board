from __future__ import annotations

from typing import Any


def normalize_string_list(value: Any, *, max_items: int = 50) -> list[str]:
    """Coerce Gemini/list fields to hashable string lists."""
    if not value:
        return []
    if not isinstance(value, list):
        value = [value]
    out: list[str] = []
    for item in value:
        if len(out) >= max_items:
            break
        if item is None:
            continue
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append(text)
            continue
        if isinstance(item, dict):
            for key in ("name", "title", "text", "label", "framework", "step", "process"):
                raw = item.get(key)
                if raw:
                    text = str(raw).strip()
                    if text:
                        out.append(text)
                        break
            else:
                text = str(item).strip()
                if text and text not in {"{}", "[]"}:
                    out.append(text)
            continue
        text = str(item).strip()
        if text:
            out.append(text)
    return out
