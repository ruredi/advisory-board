from __future__ import annotations

import unittest

from memory_builder.dedup.knowledge_dedup import filter_speaker_content


LABELED_FIXTURE = """Alex Hormozi:
The offer is the vehicle.

Speaker 1:
What do you mean by vehicle?

Alex Hormozi:
It carries the customer from pain to outcome.
"""


class KnowledgeDedupSpeakerFilterTests(unittest.TestCase):
    def test_labeled_transcript_keeps_only_persona(self) -> None:
        filtered = filter_speaker_content(
            LABELED_FIXTURE,
            ["Alex Hormozi"],
            display_name="Alex Hormozi",
        )
        self.assertIn("The offer is the vehicle.", filtered)
        self.assertIn("It carries the customer from pain to outcome.", filtered)
        self.assertNotIn("What do you mean by vehicle?", filtered)

    def test_plain_transcript_uses_heuristic(self) -> None:
        plain = "When I think about pricing, you should raise prices carefully."
        filtered = filter_speaker_content(plain, ["Alex Hormozi"], display_name="Alex Hormozi")
        self.assertIn("When I think about pricing", filtered)

    def test_x_post_with_timestamps_not_treated_as_labeled_transcript(self) -> None:
        tweet = """Thu Jul 02 08:56:30 +0000 2026
Elon Musk literally sat down for a 45-minute talk with Y Combinator.

1. Don't try to build something great. Try to build https://t.co/abc

replies: 77 | retweets: 1421 | likes: 5654 | views: 502531"""
        filtered = filter_speaker_content(tweet, ["Elon Musk"], display_name="Elon Musk")
        self.assertIn("Elon Musk literally sat down", filtered)
        self.assertTrue(filtered.strip())


if __name__ == "__main__":
    unittest.main()
