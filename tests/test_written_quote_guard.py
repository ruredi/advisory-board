from __future__ import annotations

import unittest

from memory_builder.extraction.extractor import _payload_to_units
from memory_builder.processors.speaker_turns import enrich_quote


class WrittenQuoteGuardTests(unittest.TestCase):
    def test_third_party_attribution_is_dropped(self) -> None:
        enriched = enrich_quote(
            {
                "text": "I love this product",
                "is_verbatim": True,
                "speaker": "Alex Hormozi",
                "quote_attribution": "third_party",
            },
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            segments=None,
            source_url="https://instagram.com/p/abc",
            source_title="Post",
        )
        self.assertIsNone(enriched)

    def test_non_persona_speaker_is_dropped_without_segments(self) -> None:
        enriched = enrich_quote(
            {
                "text": "What should I charge?",
                "is_verbatim": True,
                "speaker": "Customer",
            },
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            segments=None,
            source_url="https://instagram.com/p/abc",
            source_title="Post",
        )
        self.assertIsNone(enriched)

    def test_persona_written_quote_kept(self) -> None:
        enriched = enrich_quote(
            {
                "text": "Charge more than you think.",
                "is_verbatim": True,
                "speaker": "Alex Hormozi",
            },
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            segments=None,
            source_url="https://instagram.com/p/abc",
            source_title="Post",
        )
        self.assertIsNotNone(enriched)

    def test_extractor_drops_third_party_written_quote(self) -> None:
        units = _payload_to_units(
            [
                {
                    "content_type": "quote",
                    "chunk_text": "Client quote",
                    "quotes": [
                        {
                            "text": "This changed my business",
                            "is_verbatim": True,
                            "speaker": "Alex Hormozi",
                            "quote_attribution": "third_party",
                        }
                    ],
                }
            ],
            persona_id="hormozi",
            source_id=1,
            default_source_nature="written",
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            source_url="https://instagram.com/p/abc",
            source_title="Caption post",
            segments=None,
        )
        self.assertEqual(units, [])


if __name__ == "__main__":
    unittest.main()
