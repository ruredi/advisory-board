from __future__ import annotations

import unittest

from memory_builder.extraction.extractor import _payload_to_units
from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments


def sample_segments() -> TranscriptSegments:
    return TranscriptSegments(
        display_name="Alex Hormozi",
        segments=[
            TranscriptSegment(
                segment_id="seg-1",
                speaker="Alex Hormozi",
                speaker_type="target",
                text="Raise prices when demand exceeds capacity.",
                start_seconds=42.0,
            ),
            TranscriptSegment(
                segment_id="seg-2",
                speaker="Speaker 1",
                speaker_type="other",
                text="Can you repeat that?",
                start_seconds=50.0,
            ),
        ],
    )


class QuoteGuardTests(unittest.TestCase):
    def test_host_quote_payload_is_dropped(self) -> None:
        units = _payload_to_units(
            [
                {
                    "content_type": "quote",
                    "chunk_text": "Host asks for repeat",
                    "quotes": [
                        {
                            "text": "Can you repeat that?",
                            "is_verbatim": True,
                            "speaker": "Speaker 1",
                        }
                    ],
                }
            ],
            persona_id="hormozi",
            source_id=1,
            default_source_nature="natural_spoken",
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            source_url="https://example.com/ep",
            source_title="Episode",
            segments=sample_segments(),
        )
        self.assertEqual(units, [])

    def test_persona_quote_is_kept_with_source_link(self) -> None:
        units = _payload_to_units(
            [
                {
                    "content_type": "quote",
                    "chunk_text": "Pricing advice",
                    "quotes": [
                        {
                            "text": "Raise prices when demand exceeds capacity.",
                            "is_verbatim": True,
                            "speaker": "Alex Hormozi",
                        }
                    ],
                }
            ],
            persona_id="hormozi",
            source_id=1,
            default_source_nature="natural_spoken",
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            source_url="https://www.youtube.com/watch?v=abc123",
            source_title="Interview",
            segments=sample_segments(),
        )
        self.assertEqual(len(units), 1)
        quote = units[0].quotes[0]
        self.assertEqual(quote["segment_id"], "seg-1")
        self.assertIn("t=42", quote["source_link"])


if __name__ == "__main__":
    unittest.main()
