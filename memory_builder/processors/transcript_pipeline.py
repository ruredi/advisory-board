from __future__ import annotations

from pathlib import Path

from memory_builder.processors.diarized_transcript import (
    TranscriptSegments,
    render_labeled_transcript,
    save_transcript_artifacts,
    transcribe_audio_with_gemini_diarized,
)
from memory_builder.processors.speaker_turns import build_extraction_input, extract_target_segments


def build_diarized_document_text(
    *,
    audio_path: Path,
    transcription_model: str,
    display_name: str,
    speaker_names: list[str],
    processed_dir: Path,
) -> tuple[str, TranscriptSegments, dict[str, str]]:
    segments = transcribe_audio_with_gemini_diarized(
        audio_path,
        transcription_model,
        display_name,
        speaker_names,
    )
    labeled_transcript = render_labeled_transcript(segments)
    persona_transcript = extract_target_segments(segments)
    extraction_input = build_extraction_input(segments)
    artifact_paths = save_transcript_artifacts(
        processed_dir,
        segments=segments,
        labeled_transcript=labeled_transcript,
        persona_transcript=persona_transcript,
        extraction_input=extraction_input,
    )
    return extraction_input, segments, artifact_paths
