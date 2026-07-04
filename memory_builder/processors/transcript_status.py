from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory_builder.fetch.downloader import source_slug
from memory_builder.paths import project_root, sources_processed_dir, sources_raw_dir

TRANSCRIPT_VARIANTS = (
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
    mode = str(meta.get("transcription_mode", ""))
    segments_path = processed_dir / "transcript_segments.json"

    if source_status == "failed" and meta.get("diarization_error"):
        return "failed_diarization"
    if segments_path.exists() and mode == "diarized":
        return "labeled"
    if mode in {"fallback_vtt", "plain_vtt"}:
        return "fallback"
    if source_type in {"youtube", "podcast"} and (processed_dir / "document.txt").exists():
        if mode in {"plain", ""} and not segments_path.exists():
            return "unlabeled"
    return "unlabeled"


def list_transcript_variants(processed_dir: Path) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for key, filename, label in TRANSCRIPT_VARIANTS:
        path = processed_dir / filename
        if key == "labeled" and not path.exists():
            continue
        if not path.exists() and key != "document":
            variants.append(
                {
                    "key": key,
                    "label": label,
                    "available": False,
                    "char_count": 0,
                }
            )
            continue
        doc_path = processed_dir / "document.txt"
        effective = path if path.exists() else (doc_path if key == "document" else None)
        if effective is None or not effective.exists():
            variants.append({"key": key, "label": label, "available": False, "char_count": 0})
            continue
        text = effective.read_text(encoding="utf-8")
        variants.append(
            {
                "key": key,
                "label": label,
                "available": True,
                "char_count": len(text),
            }
        )
    return variants


def read_transcript_variant(processed_dir: Path, variant: str, *, limit: int | None = None) -> str | None:
    mapping = {key: filename for key, filename, _label in TRANSCRIPT_VARIANTS}
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
