"""Spoken-source transcript artifact layout and runtime rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory_builder.processors.diarized_transcript import TranscriptSegments, render_labeled_transcript
from memory_builder.processors.speaker_turns import extract_target_segments


ATTRIBUTION_AUDIO_DIARIZED = "audio_diarized"
ATTRIBUTION_TEXT = "text_attributed"
ATTRIBUTION_NONE = "none"


def render_plain_transcript(segments: TranscriptSegments) -> str:
    parts = [segment.text.strip() for segment in segments.segments if segment.text.strip()]
    return "\n\n".join(parts)


def save_spoken_transcript_artifacts(
    processed_dir: Path,
    *,
    segments: TranscriptSegments,
    raw_transcript: str,
    extraction_input: str,
    attribution_mode: str,
) -> dict[str, str]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw_transcript.txt": str(processed_dir / "raw_transcript.txt"),
        "transcript_segments.json": str(processed_dir / "transcript_segments.json"),
        "extraction_input.txt": str(processed_dir / "extraction_input.txt"),
        "transcript.txt": str(processed_dir / "transcript.txt"),
    }
    (processed_dir / "raw_transcript.txt").write_text(raw_transcript.strip(), encoding="utf-8")
    segment_payload = segments.to_dict()
    segment_payload["attribution_mode"] = attribution_mode
    (processed_dir / "transcript_segments.json").write_text(
        json.dumps(segment_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "extraction_input.txt").write_text(extraction_input, encoding="utf-8")
    (processed_dir / "transcript.txt").write_text(extraction_input, encoding="utf-8")
    return paths


def load_segments_file(processed_dir: Path) -> TranscriptSegments | None:
    path = processed_dir / "transcript_segments.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    segments = TranscriptSegments.from_dict(data)
    return segments if segments.segments else None


def render_variant_from_segments(processed_dir: Path, variant: str) -> str | None:
    segments = load_segments_file(processed_dir)
    if segments is None:
        return _read_legacy_variant_file(processed_dir, variant)
    if variant == "labeled":
        return render_labeled_transcript(segments)
    if variant == "persona":
        return extract_target_segments(segments)
    if variant == "document":
        return render_labeled_transcript(segments)
    if variant == "extraction_input":
        path = processed_dir / "extraction_input.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None
    return None


def _read_legacy_variant_file(processed_dir: Path, variant: str) -> str | None:
    mapping = {
        "labeled": "transcript_labeled.txt",
        "persona": "persona_transcript.txt",
        "document": "document.txt",
        "extraction_input": "extraction_input.txt",
    }
    filename = mapping.get(variant)
    if not filename:
        return None
    path = processed_dir / filename
    if not path.exists() and variant == "document":
        path = processed_dir / "transcript.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def segments_available(processed_dir: Path) -> bool:
    return (processed_dir / "transcript_segments.json").exists()


def variant_char_count(processed_dir: Path, variant: str) -> int:
    text = render_variant_from_segments(processed_dir, variant)
    return len(text) if text else 0


def attribution_mode_from_metadata(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ATTRIBUTION_NONE
    mode = str(metadata.get("attribution_mode") or metadata.get("transcription_mode") or "")
    if mode in {ATTRIBUTION_AUDIO_DIARIZED, "diarized"}:
        return ATTRIBUTION_AUDIO_DIARIZED
    if mode in {ATTRIBUTION_TEXT, "text_attributed"}:
        return ATTRIBUTION_TEXT
    return ATTRIBUTION_NONE
