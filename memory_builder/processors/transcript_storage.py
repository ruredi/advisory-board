from __future__ import annotations

import json
from pathlib import Path

from memory_builder.processors.diarized_transcript import TranscriptSegments


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
    if not file_path.exists():
        return None
    text = file_path.read_text(encoding="utf-8")
    if limit is not None:
        return text[:limit]
    return text
