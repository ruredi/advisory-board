from __future__ import annotations

import json
from pathlib import Path

from memory_builder.processors.diarized_transcript import TranscriptSegments
from memory_builder.processors.transcript_artifacts import render_variant_from_segments


def load_transcript_segments(path: Path | str | None) -> TranscriptSegments | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    data = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    segments = TranscriptSegments.from_dict(data)
    return segments if segments.segments else None


def read_processed_text(path: Path | str | None, *, limit: int | None = None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    processed_dir = file_path.parent
    if (processed_dir / "transcript_segments.json").exists():
        rendered = render_variant_from_segments(processed_dir, "document")
        if rendered:
            if limit is not None:
                return rendered[:limit]
            return rendered
    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    if limit is not None:
        return text[:limit]
    return text
