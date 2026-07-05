from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments
from memory_builder.processors.speaker_turns import build_extraction_input_with_context
from memory_builder.processors.transcript_artifacts import (
    render_variant_from_segments,
    save_spoken_transcript_artifacts,
    segments_available,
)
from memory_builder.processors.transcript_pipeline import build_text_attributed_document_text


class TranscriptPipelineTests(unittest.TestCase):
    def test_save_spoken_artifacts_without_labeled_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            segments = TranscriptSegments(
                display_name="Alex Hormozi",
                transcription_mode="text_attributed",
                segments=[
                    TranscriptSegment(
                        segment_id="seg-1",
                        speaker="Alex Hormozi",
                        speaker_type="target",
                        text="Raise prices when demand exceeds capacity.",
                    ),
                    TranscriptSegment(
                        segment_id="seg-2",
                        speaker="Speaker 1",
                        speaker_type="other",
                        text="Can you repeat that?",
                    ),
                ],
            )
            extraction_input = build_extraction_input_with_context(
                segments,
                post_context="@hormozi\nCaption about pricing",
            )
            save_spoken_transcript_artifacts(
                tmp,
                segments=segments,
                raw_transcript="Raise prices when demand exceeds capacity. Can you repeat that?",
                extraction_input=extraction_input,
                attribution_mode="text_attributed",
            )
            self.assertTrue((tmp / "raw_transcript.txt").exists())
            self.assertTrue((tmp / "transcript_segments.json").exists())
            self.assertTrue((tmp / "extraction_input.txt").exists())
            self.assertFalse((tmp / "transcript_labeled.txt").exists())
            self.assertFalse((tmp / "persona_transcript.txt").exists())
            payload = json.loads((tmp / "transcript_segments.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["attribution_mode"], "text_attributed")
            extraction = (tmp / "extraction_input.txt").read_text(encoding="utf-8")
            self.assertIn("[POST_CONTEXT]", extraction)
            self.assertIn("Caption about pricing", extraction)
            self.assertNotIn("transcript_labeled", extraction)

    def test_runtime_render_labeled_and_persona(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            segments = TranscriptSegments(
                display_name="Alex Hormozi",
                segments=[
                    TranscriptSegment(
                        segment_id="seg-1",
                        speaker="Alex Hormozi",
                        speaker_type="target",
                        text="Target line.",
                    ),
                    TranscriptSegment(
                        segment_id="seg-2",
                        speaker="Speaker 1",
                        speaker_type="other",
                        text="Host line.",
                    ),
                ],
            )
            save_spoken_transcript_artifacts(
                tmp,
                segments=segments,
                raw_transcript="Target line. Host line.",
                extraction_input="input",
                attribution_mode="text_attributed",
            )
            self.assertTrue(segments_available(tmp))
            labeled = render_variant_from_segments(tmp, "labeled")
            persona = render_variant_from_segments(tmp, "persona")
            assert labeled is not None
            assert persona is not None
            self.assertIn("Alex Hormozi:", labeled)
            self.assertIn("Host line.", labeled)
            self.assertIn("Target line.", persona)
            self.assertNotIn("Host line.", persona)

    @patch("memory_builder.processors.transcript_pipeline.attribute_transcript_text_with_gemini")
    def test_text_attributed_pipeline_writes_artifacts(self, mock_attribute) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            mock_attribute.return_value = TranscriptSegments(
                display_name="Alex Hormozi",
                transcription_mode="text_attributed",
                segments=[
                    TranscriptSegment(
                        segment_id="seg-1",
                        speaker="Alex Hormozi",
                        speaker_type="target",
                        text="hello from supadata transcript without punctuation",
                    )
                ],
            )
            extraction_input, segments, paths = build_text_attributed_document_text(
                raw_transcript="hello from supadata transcript without punctuation",
                transcription_model="gemini-2.5-flash",
                display_name="Alex Hormozi",
                speaker_names=["Alex Hormozi"],
                processed_dir=tmp,
                post_context="@hormozi\nReel caption",
            )
            self.assertIn("[POST_CONTEXT]", extraction_input)
            self.assertIn("Reel caption", extraction_input)
            self.assertEqual(len(segments.segments), 1)
            self.assertIn("transcript_segments.json", paths)


if __name__ == "__main__":
    unittest.main()
