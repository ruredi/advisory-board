from __future__ import annotations

from pathlib import Path

from memory_builder.processors.diarized_transcript import (
    TranscriptSegments,
    attribute_transcript_text_with_gemini,
    transcribe_audio_with_gemini_diarized,
)
from memory_builder.processors.speaker_turns import (
    build_extraction_input,
    build_extraction_input_with_context,
)
from memory_builder.processors.transcript_artifacts import (
    ATTRIBUTION_AUDIO_DIARIZED,
    ATTRIBUTION_TEXT,
    save_spoken_transcript_artifacts,
)


def build_diarized_document_text(
    *,
    audio_path: Path,
    transcription_model: str,
    display_name: str,
    speaker_names: list[str],
    processed_dir: Path,
    source_context: str = "",
) -> tuple[str, TranscriptSegments, dict[str, str]]:
    segments = transcribe_audio_with_gemini_diarized(
        audio_path,
        transcription_model,
        display_name,
        speaker_names,
    )
    segments.transcription_mode = "diarized"
    raw_transcript = _plain_text_from_segments(segments)
    extraction_input = build_extraction_input_with_context(
        segments,
        source_context=source_context,
    )
    artifact_paths = save_spoken_transcript_artifacts(
        processed_dir,
        segments=segments,
        raw_transcript=raw_transcript,
        extraction_input=extraction_input,
        attribution_mode=ATTRIBUTION_AUDIO_DIARIZED,
    )
    return extraction_input, segments, artifact_paths


def build_text_attributed_document_text(
    *,
    raw_transcript: str,
    transcription_model: str,
    display_name: str,
    speaker_names: list[str],
    processed_dir: Path,
    post_context: str = "",
    source_context: str = "",
    ocr_context: str = "",
) -> tuple[str, TranscriptSegments, dict[str, str]]:
    segments = attribute_transcript_text_with_gemini(
        raw_transcript,
        transcription_model,
        display_name,
        speaker_names,
        post_context=post_context,
        source_context=source_context,
    )
    extraction_input = build_extraction_input_with_context(
        segments,
        post_context=post_context,
        source_context=source_context,
        ocr_context=ocr_context,
    )
    artifact_paths = save_spoken_transcript_artifacts(
        processed_dir,
        segments=segments,
        raw_transcript=raw_transcript.strip(),
        extraction_input=extraction_input,
        attribution_mode=ATTRIBUTION_TEXT,
    )
    return extraction_input, segments, artifact_paths


def _plain_text_from_segments(segments: TranscriptSegments) -> str:
    parts = [segment.text.strip() for segment in segments.segments if segment.text.strip()]
    return "\n\n".join(parts)
