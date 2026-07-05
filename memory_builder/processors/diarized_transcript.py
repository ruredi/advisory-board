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


def build_text_attribution_prompt(
    display_name: str,
    speaker_names: list[str],
    *,
    post_context: str = "",
    source_context: str = "",
) -> str:
    aliases = ", ".join(dict.fromkeys([display_name, *speaker_names]))
    context_blocks: list[str] = []
    if post_context.strip():
        context_blocks.append(f"Post/caption context (not spoken transcript):\n{post_context.strip()}")
    if source_context.strip():
        context_blocks.append(f"Source context:\n{source_context.strip()}")
    context_section = "\n\n".join(context_blocks)
    context_note = (
        f"\n\nAdditional context for speaker identification (do not merge into transcript segments):\n{context_section}"
        if context_section
        else ""
    )
    return f"""Segment this transcript text for a knowledge indexing pipeline.

Return ONLY valid JSON with this shape:
{{
  "segments": [
    {{
      "segment_id": "seg-1",
      "speaker": "{display_name}",
      "speaker_type": "target",
      "text": "verbatim text from transcript",
      "start_seconds": null,
      "end_seconds": null,
      "confidence": "strong"
    }}
  ]
}}

Rules:
- Input is a plain transcript without reliable speaker labels. Infer speaker turns from dialogue cues.
- Identify the target person as "{display_name}" when confident. Aliases: {aliases}.
- Label all other speakers as "Speaker 1", "Speaker 2", etc. Keep speaker IDs consistent across turns.
- Use speaker_type "target" only for {display_name}. Use "other" for hosts/interviewers/guests/audience. Use "unknown" when unsure.
- One speaker turn per segment. Do not summarize. Preserve exact wording from the transcript.
- If the transcript appears to be a single speaker on an official account with no clear alternation, you may use one target segment with confidence "medium".
- Do not invent content that is not in the transcript.{context_note}

Transcript text:
"""


def attribute_transcript_text_with_gemini(
    raw_transcript: str,
    model: str,
    display_name: str,
    speaker_names: list[str],
    *,
    post_context: str = "",
    source_context: str = "",
) -> TranscriptSegments:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required for text speaker attribution")

    cleaned = raw_transcript.strip()
    if not cleaned:
        raise RuntimeError("Cannot attribute empty transcript text")

    from google.genai import types

    client = build_gemini_client(api_key, timeout_ms=300_000)
    prompt = build_text_attribution_prompt(
        display_name,
        speaker_names,
        post_context=post_context,
        source_context=source_context,
    )
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=f"{prompt}{cleaned}")])],
        config={"response_mime_type": "application/json", "response_schema": SEGMENT_SCHEMA},
    )
    payload = _parse_json_object(response.text or "{}")
    segments = TranscriptSegments.from_dict(payload)
    segments.display_name = display_name
    segments.transcription_mode = "text_attributed"
    if not segments.segments:
        raise RuntimeError("Gemini returned no attributed segments for transcript text")

    ctx = get_run_context()
    if ctx:
        ctx.record_gemini(
            response=response,
            operation="transcription",
            model=model,
            input_modality="text",
            metadata={
                "transcript_chars": len(cleaned),
                "segment_count": len(segments.segments),
                "transcription_mode": "text_attributed",
            },
        )
    return segments


def save_transcript_artifacts(
    processed_dir: Path,
    *,
    segments: TranscriptSegments,
    labeled_transcript: str,
    persona_transcript: str,
    extraction_input: str,
) -> dict[str, str]:
    from memory_builder.processors.transcript_artifacts import (
        ATTRIBUTION_AUDIO_DIARIZED,
        save_spoken_transcript_artifacts,
    )

    mode = (
        ATTRIBUTION_AUDIO_DIARIZED
        if segments.transcription_mode in {"diarized", ATTRIBUTION_AUDIO_DIARIZED}
        else segments.transcription_mode or ATTRIBUTION_AUDIO_DIARIZED
    )
    raw_transcript = "\n\n".join(segment.text.strip() for segment in segments.segments if segment.text.strip())
    return save_spoken_transcript_artifacts(
        processed_dir,
        segments=segments,
        raw_transcript=raw_transcript,
        extraction_input=extraction_input,
        attribution_mode=mode,
    )


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
