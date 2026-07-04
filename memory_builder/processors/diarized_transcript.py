from __future__ import annotations

import json
import mimetypes
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from memory_builder.gemini_client import build_gemini_client
from memory_builder.telemetry.context import get_run_context

INLINE_AUDIO_MAX_BYTES = 18 * 1024 * 1024

SEGMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "string"},
                    "speaker": {"type": "string"},
                    "speaker_type": {"type": "string", "enum": ["target", "other", "unknown"]},
                    "text": {"type": "string"},
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "confidence": {"type": "string"},
                },
                "required": ["segment_id", "speaker", "speaker_type", "text"],
            },
        }
    },
    "required": ["segments"],
}


@dataclass
class TranscriptSegment:
    segment_id: str
    speaker: str
    speaker_type: str
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSegments:
    segments: list[TranscriptSegment] = field(default_factory=list)
    display_name: str = ""
    transcription_mode: str = "diarized"

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "transcription_mode": self.transcription_mode,
            "segments": [segment.to_dict() for segment in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptSegments:
        segments = [
            TranscriptSegment(
                segment_id=str(item.get("segment_id", f"seg-{index + 1}")),
                speaker=str(item.get("speaker", "Speaker 1")),
                speaker_type=str(item.get("speaker_type", "unknown")),
                text=str(item.get("text", "")).strip(),
                start_seconds=_optional_float(item.get("start_seconds")),
                end_seconds=_optional_float(item.get("end_seconds")),
                confidence=str(item.get("confidence", "medium")),
            )
            for index, item in enumerate(data.get("segments") or [])
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]
        return cls(
            segments=segments,
            display_name=str(data.get("display_name", "")),
            transcription_mode=str(data.get("transcription_mode", "diarized")),
        )


def build_diarized_transcribe_prompt(display_name: str, speaker_names: list[str]) -> str:
    aliases = ", ".join(dict.fromkeys([display_name, *speaker_names]))
    return f"""Transcribe this audio verbatim for a knowledge indexing pipeline.

Return ONLY valid JSON with this shape:
{{
  "segments": [
    {{
      "segment_id": "seg-1",
      "speaker": "{display_name}",
      "speaker_type": "target",
      "text": "verbatim text",
      "start_seconds": 0,
      "end_seconds": 12,
      "confidence": "strong"
    }}
  ]
}}

Rules:
- Identify the target person as "{display_name}" when you are confident. Aliases: {aliases}.
- Label all other speakers as "Speaker 1", "Speaker 2", etc. Keep speaker IDs consistent.
- Use speaker_type "target" only for {display_name}. Use "other" for hosts/interviewers/guests. Use "unknown" when unsure.
- One speaker turn per segment. Do not summarize. Preserve exact wording.
- Include start_seconds and end_seconds when possible.
- Do not invent speakers or merge unrelated turns.
"""


def transcribe_audio_with_gemini_diarized(
    audio_path: Path,
    model: str,
    display_name: str,
    speaker_names: list[str],
) -> TranscriptSegments:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required for diarized transcription")

    from google.genai import types

    client = build_gemini_client(api_key, timeout_ms=300_000)
    prompt = build_diarized_transcribe_prompt(display_name, speaker_names)
    audio_bytes = audio_path.read_bytes()
    mime_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"

    if len(audio_bytes) <= INLINE_AUDIO_MAX_BYTES:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    ],
                )
            ],
            config={"response_mime_type": "application/json", "response_schema": SEGMENT_SCHEMA},
        )
    else:
        uploaded = client.files.upload(file=audio_path)
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type or mime_type),
                    ],
                )
            ],
            config={"response_mime_type": "application/json", "response_schema": SEGMENT_SCHEMA},
        )

    payload = _parse_json_object(response.text or "{}")
    segments = TranscriptSegments.from_dict(payload)
    segments.display_name = display_name
    segments.transcription_mode = "diarized"
    if not segments.segments:
        raise RuntimeError(f"Gemini returned no diarized segments for {audio_path.name}")

    ctx = get_run_context()
    if ctx:
        ctx.record_gemini(
            response=response,
            operation="transcription",
            model=model,
            input_modality="audio",
            metadata={
                "audio_bytes": len(audio_bytes),
                "audio_file": audio_path.name,
                "segment_count": len(segments.segments),
                "transcription_mode": "diarized",
            },
        )
    return segments


def render_labeled_transcript(segments: TranscriptSegments) -> str:
    blocks: list[str] = []
    for segment in segments.segments:
        blocks.append(f"{segment.speaker}:\n{segment.text.strip()}")
    return "\n\n".join(blocks)


def save_transcript_artifacts(
    processed_dir: Path,
    *,
    segments: TranscriptSegments,
    labeled_transcript: str,
    persona_transcript: str,
    extraction_input: str,
) -> dict[str, str]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "transcript_segments.json": str(processed_dir / "transcript_segments.json"),
        "transcript_labeled.txt": str(processed_dir / "transcript_labeled.txt"),
        "document.txt": str(processed_dir / "document.txt"),
        "persona_transcript.txt": str(processed_dir / "persona_transcript.txt"),
        "extraction_input.txt": str(processed_dir / "extraction_input.txt"),
        "transcript.txt": str(processed_dir / "transcript.txt"),
    }
    (processed_dir / "transcript_segments.json").write_text(
        json.dumps(segments.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (processed_dir / "transcript_labeled.txt").write_text(labeled_transcript, encoding="utf-8")
    (processed_dir / "document.txt").write_text(labeled_transcript, encoding="utf-8")
    (processed_dir / "persona_transcript.txt").write_text(persona_transcript, encoding="utf-8")
    (processed_dir / "extraction_input.txt").write_text(extraction_input, encoding="utf-8")
    (processed_dir / "transcript.txt").write_text(extraction_input, encoding="utf-8")
    return paths


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_json_object(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {}
