from __future__ import annotations

import unittest

from memory_builder.discovery.source_discovery import score_candidate
from memory_builder.source_registry import SourceCandidate, approved_to_social_profiles, ApprovedSources
from memory_builder.source_review import apply_review, parse_reject_indices


class SourceScoringTests(unittest.TestCase):
    def test_official_site_scores_highest(self) -> None:
        score, signals = score_candidate(
            "https://x.com/alexhormozi",
            "official_site",
            ["acquisition.com"],
        )
        self.assertGreaterEqual(score, 0.95)
        self.assertIn("official_site", signals)

    def test_aggregator_scores_low(self) -> None:
        score, signals = score_candidate(
            "https://threadreaderapp.com/user/AlexHormozi",
            "seed_file",
            ["acquisition.com"],
        )
        self.assertLessEqual(score, 0.45)
        self.assertIn("aggregator", signals)


class SourceReviewTests(unittest.TestCase):
    def test_parse_reject_indices(self) -> None:
        self.assertEqual(parse_reject_indices("2, 4", 5), {2, 4})
        self.assertEqual(parse_reject_indices("", 5), set())

    def test_apply_review_rejects_and_manual(self) -> None:
        candidates = [
            SourceCandidate(
                url="https://x.com/alexhormozi",
                platform="x",
                confidence=0.96,
                discovery_source="official_site",
                username="alexhormozi",
            ),
            SourceCandidate(
                url="https://www.facebook.com/ahormozi/",
                platform="facebook",
                confidence=0.72,
                discovery_source="seed_file",
                username="ahormozi",
            ),
        ]
        approved = apply_review(
            candidates,
            rejected_indices={2},
            manual_urls=["https://www.tiktok.com/@hormozi"],
            persona_id="hormozi",
            reviewed_by="test",
        )
        urls = [source.url for source in approved.sources]
        self.assertIn("https://x.com/alexhormozi", urls)
        self.assertIn("https://tiktok.com/@hormozi", urls)
        self.assertNotIn("https://www.facebook.com/ahormozi/", urls)

    def test_approved_to_social_profiles(self) -> None:
        approved = ApprovedSources(
            persona_id="hormozi",
            reviewed_at="2026-01-01T00:00:00+00:00",
            reviewed_by="test",
            sources=[
                SourceCandidate(
                    url="https://x.com/alexhormozi",
                    platform="x",
                    confidence=0.96,
                    discovery_source="official_site",
                    username="alexhormozi",
                ),
                SourceCandidate(
                    url="https://www.youtube.com/@AlexHormozi",
                    platform="youtube",
                    confidence=0.94,
                    discovery_source="watch_feed",
                    username="AlexHormozi",
                ),
            ],
        )
        profiles = approved_to_social_profiles(approved)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["platform"], "x")


if __name__ == "__main__":
    unittest.main()
