from __future__ import annotations

import unittest

from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments
from memory_builder.processors.speaker_turns import (
    build_extraction_input,
    build_source_link,
    enrich_quote,
    extract_target_segments,
    filter_speaker_content_labeled,
    is_labeled_transcript,
    quote_origin_for_text,
)


LABELED_FIXTURE = """Alex Hormozi:
The offer is the vehicle.

Speaker 1:
What do you mean by vehicle?

Alex Hormozi:
It carries the customer from pain to outcome.
"""


def sample_segments() -> TranscriptSegments:
    return TranscriptSegments(
        display_name="Alex Hormozi",
        segments=[
            TranscriptSegment(
                segment_id="seg-1",
                speaker="Alex Hormozi",
                speaker_type="target",
                text="The offer is the vehicle.",
                start_seconds=12.0,
            ),
            TranscriptSegment(
                segment_id="seg-2",
                speaker="Speaker 1",
                speaker_type="other",
                text="What do you mean by vehicle?",
                start_seconds=18.0,
            ),
            TranscriptSegment(
                segment_id="seg-3",
                speaker="Alex Hormozi",
                speaker_type="target",
                text="It carries the customer from pain to outcome.",
                start_seconds=25.5,
            ),
        ],
    )


class SpeakerTurnsTests(unittest.TestCase):
    def test_is_labeled_transcript(self) -> None:
        self.assertTrue(is_labeled_transcript(LABELED_FIXTURE))
        self.assertFalse(is_labeled_transcript("plain paragraph without labels"))

    def test_is_labeled_transcript_rejects_x_post_colons(self) -> None:
        tweet = """Thu Jul 02 08:56:30 +0000 2026
Elon Musk literally sat down for a 45-minute talk.

replies: 77 | retweets: 1421 | likes: 5654 | views: 502531"""
        self.assertFalse(is_labeled_transcript(tweet))

    def test_extract_target_segments(self) -> None:
        text = extract_target_segments(sample_segments())
        self.assertIn("The offer is the vehicle.", text)
        self.assertIn("It carries the customer from pain to outcome.", text)
        self.assertNotIn("What do you mean", text)

    def test_build_extraction_input_marks_context(self) -> None:
        text = build_extraction_input(sample_segments())
        self.assertIn("[Alex Hormozi]", text)
        self.assertIn("[CONTEXT_ONLY - Speaker 1]", text)
        self.assertIn("What do you mean by vehicle?", text)

    def test_quote_origin_for_target_segment(self) -> None:
        origin = quote_origin_for_text(
            "It carries the customer from pain to outcome.",
            sample_segments(),
            source_url="https://www.youtube.com/watch?v=abc123",
            source_title="Interview",
        )
        self.assertIsNotNone(origin)
        assert origin is not None
        self.assertEqual(origin.segment_id, "seg-3")
        self.assertEqual(origin.speaker_type, "target")
        self.assertIn("t=25", origin.source_link)

    def test_quote_origin_rejects_host_text(self) -> None:
        origin = quote_origin_for_text(
            "What do you mean by vehicle?",
            sample_segments(),
            source_url="https://example.com/ep",
            source_title="Episode",
        )
        self.assertIsNone(origin)

    def test_enrich_quote_drops_host_quote(self) -> None:
        enriched = enrich_quote(
            {"text": "What do you mean by vehicle?", "is_verbatim": True, "speaker": "Speaker 1"},
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            segments=sample_segments(),
            source_url="https://example.com/ep",
            source_title="Episode",
        )
        self.assertIsNone(enriched)

    def test_enrich_quote_keeps_persona_quote(self) -> None:
        enriched = enrich_quote(
            {
                "text": "It carries the customer from pain to outcome.",
                "is_verbatim": True,
                "speaker": "Alex Hormozi",
            },
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            segments=sample_segments(),
            source_url="https://www.youtube.com/watch?v=abc123",
            source_title="Interview",
        )
        self.assertIsNotNone(enriched)
        assert enriched is not None
        self.assertEqual(enriched["segment_id"], "seg-3")
        self.assertIn("t=25", enriched["source_link"])

    def test_filter_speaker_content_labeled(self) -> None:
        filtered = filter_speaker_content_labeled(LABELED_FIXTURE, "Alex Hormozi", ["Alex Hormozi"])
        self.assertIn("The offer is the vehicle.", filtered)
        self.assertNotIn("What do you mean by vehicle?", filtered)

    def test_build_source_link_youtube(self) -> None:
        link = build_source_link("https://www.youtube.com/watch?v=abc123", 90.2)
        self.assertIn("t=90", link)


if __name__ == "__main__":
    unittest.main()
