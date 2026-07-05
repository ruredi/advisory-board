from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory_builder.fetch.downloader import source_slug
from memory_builder.paths import project_root, sources_processed_dir, sources_raw_dir
from memory_builder.processors.transcript_artifacts import (
    render_variant_from_segments,
    segments_available,
    variant_char_count,
)

TRANSCRIPT_VARIANTS = (
    ("segments", "", "Segmentek"),
    ("document", "document.txt", "Teljes transcript"),
    ("labeled", "transcript_labeled.txt", "Címkézett transcript"),
    ("persona", "persona_transcript.txt", "Persona transcript"),
    ("extraction_input", "extraction_input.txt", "Extraction input"),
)


def processed_dir_for_source(persona_id: str, source_url: str, root: Path | None = None) -> Path:
    base_root = root or project_root()
    return sources_processed_dir(persona_id, base_root) / source_slug(source_url)


def load_source_metadata(persona_id: str, source_url: str, root: Path | None = None) -> dict[str, Any]:
    base_root = root or project_root()
    path = sources_raw_dir(persona_id, base_root) / source_slug(source_url) / "metadata.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def transcript_status_for_source(
    *,
    source_type: str,
    source_status: str,
    processed_dir: Path,
    metadata: dict[str, Any] | None = None,
) -> str:
    meta = metadata or {}
    mode = str(meta.get("attribution_mode") or meta.get("transcription_mode", ""))
    segments_path = processed_dir / "transcript_segments.json"

    if source_status == "failed" and meta.get("diarization_error"):
        return "failed_diarization"
    if segments_path.exists() and mode in {"diarized", "text_attributed", "audio_diarized"}:
        return "labeled"
    if mode in {"fallback_vtt", "plain_vtt"}:
        return "fallback"
    if source_type in {"youtube", "podcast", "social"} and (processed_dir / "document.txt").exists():
        if mode in {"plain", ""} and not segments_path.exists():
            return "unlabeled"
    return "unlabeled"


def list_transcript_variants(processed_dir: Path) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    has_segments = segments_available(processed_dir)
    for key, filename, label in TRANSCRIPT_VARIANTS:
        if key == "segments":
            variants.append(
                {
                    "key": key,
                    "label": label,
                    "available": has_segments,
                    "char_count": 0,
                }
            )
            continue
        rendered = render_variant_from_segments(processed_dir, key)
        legacy_path = processed_dir / filename if filename else None
        if rendered is None and legacy_path is not None and legacy_path.exists():
            rendered = legacy_path.read_text(encoding="utf-8")
        if key == "document" and rendered is None:
            transcript_path = processed_dir / "transcript.txt"
            if transcript_path.exists():
                rendered = transcript_path.read_text(encoding="utf-8")
        available = bool(rendered and rendered.strip())
        variants.append(
            {
                "key": key,
                "label": label,
                "available": available,
                "char_count": len(rendered) if rendered else variant_char_count(processed_dir, key),
            }
        )
    return variants


def read_transcript_variant(processed_dir: Path, variant: str, *, limit: int | None = None) -> str | None:
    if variant == "segments":
        return None
    text = render_variant_from_segments(processed_dir, variant)
    if text is None:
        mapping = {key: filename for key, filename, _label in TRANSCRIPT_VARIANTS if filename}
        filename = mapping.get(variant)
        if not filename:
            return None
        path = processed_dir / filename
        if not path.exists() and variant == "document":
            path = processed_dir / "transcript.txt"
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
    if limit is not None:
        return text[:limit]
    return text
