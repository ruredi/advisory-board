from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from memory_builder.discovery.seed_links import (
    classify_source_type,
    is_processable_source,
    is_social_post_url,
    is_social_profile_url,
)
from memory_builder.discovery.social_profiles import discover_social_sources
from memory_builder.fetch.scrapfly_facebook import (
    extract_stories_from_html,
    facebook_post_public_url,
    format_facebook_post_text,
    is_group_official_post,
    parse_facebook_target,
)
from memory_builder.models import SourceType
from memory_builder.source_registry import ApprovedSources, SourceCandidate, approved_scraper_profiles


class FacebookUrlTests(unittest.TestCase):
    def test_personal_page_profile(self) -> None:
        target = parse_facebook_target("https://www.facebook.com/ahormozi/")
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "page")
        self.assertEqual(target.slug, "ahormozi")
        self.assertTrue(is_social_profile_url("https://www.facebook.com/ahormozi/"))

    def test_business_page_profile(self) -> None:
        target = parse_facebook_target("https://www.facebook.com/Acquisitioncom/")
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "page")

    def test_group_profile(self) -> None:
        target = parse_facebook_target("https://www.facebook.com/groups/acquisitioncom/")
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "group")
        self.assertTrue(is_social_profile_url("https://www.facebook.com/groups/acquisitioncom/"))

    def test_group_post_url(self) -> None:
        url = "https://www.facebook.com/groups/acquisitioncom/posts/1234567890/"
        self.assertTrue(is_social_post_url(url))
        target = parse_facebook_target(url)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "post")

    def test_reel_post_url(self) -> None:
        url = "https://www.facebook.com/reel/27070999992600212/"
        self.assertTrue(is_social_post_url(url))
        self.assertEqual(classify_source_type(url), SourceType.SOCIAL)
        self.assertTrue(is_processable_source(url))

    def test_profile_url_not_processable_as_seed(self) -> None:
        self.assertFalse(is_processable_source("https://www.facebook.com/ahormozi/"))


class FacebookStoryParsingTests(unittest.TestCase):
    def test_extract_story_from_json_script(self) -> None:
        payload = {
            "data": {
                "post_id": "914955354947975",
                "message": {"text": "Solve rich people’s problems."},
                "wwwURL": "https://www.facebook.com/reel/27070999992600212/",
                "actors": [{"__typename": "User", "name": "Alex Hormozi", "id": "100093005555209"}],
            }
        }
        html = f'<script type="application/json">{json.dumps(payload)}</script>'
        stories = extract_stories_from_html(html)
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["post_id"], "914955354947975")
        self.assertIn("rich people", stories[0]["text"])

    def test_group_official_post_filter(self) -> None:
        official = {
            "actors": [{"typename": "Group", "name": "Acquisition.com", "id": "123"}],
        }
        member = {
            "actors": [{"typename": "User", "name": "Random Member", "id": "999"}],
        }
        self.assertTrue(is_group_official_post(official, "acquisitioncom"))
        self.assertFalse(is_group_official_post(member, "acquisitioncom"))

    def test_format_facebook_post_text(self) -> None:
        text = format_facebook_post_text(
            {
                "text": "Offer is the problem.",
                "actors": [{"name": "Alex Hormozi"}],
                "wwwURL": "https://www.facebook.com/reel/123/",
            }
        )
        self.assertIn("Alex Hormozi", text)
        self.assertIn("Offer is the problem.", text)
        self.assertIn("facebook.com/reel/123", text)

    def test_facebook_post_public_url_prefers_www_url(self) -> None:
        url = facebook_post_public_url(
            {"post_id": "1", "wwwURL": "https://www.facebook.com/reel/123/"},
            "https://www.facebook.com/ahormozi/",
        )
        self.assertEqual(url, "https://www.facebook.com/reel/123/")


class FacebookScraperSelectionTests(unittest.TestCase):
    def test_skip_facebook_when_instagram_approved(self) -> None:
        approved = ApprovedSources(
            persona_id="hormozi",
            reviewed_at="2026-01-01T00:00:00+00:00",
            reviewed_by="test",
            sources=[
                SourceCandidate(
                    url="https://instagram.com/hormozi",
                    platform="instagram",
                    confidence=0.9,
                    discovery_source="seed_file",
                    username="hormozi",
                ),
                SourceCandidate(
                    url="https://facebook.com/ahormozi",
                    platform="facebook",
                    confidence=0.9,
                    discovery_source="seed_file",
                    username="ahormozi",
                ),
            ],
        )
        profiles = approved_scraper_profiles(approved)
        platforms = {profile["platform"] for profile in profiles}
        self.assertIn("instagram", platforms)
        self.assertNotIn("facebook", platforms)

    def test_use_facebook_when_no_instagram(self) -> None:
        approved = ApprovedSources(
            persona_id="example",
            reviewed_at="2026-01-01T00:00:00+00:00",
            reviewed_by="test",
            sources=[
                SourceCandidate(
                    url="https://facebook.com/ahormozi",
                    platform="facebook",
                    confidence=0.9,
                    discovery_source="seed_file",
                    username="ahormozi",
                ),
            ],
        )
        profiles = approved_scraper_profiles(approved)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["platform"], "facebook")
        self.assertEqual(profiles[0]["facebook_kind"], "page")


class FacebookDiscoveryTests(unittest.TestCase):
    @patch("memory_builder.discovery.social_profiles.run_async")
    @patch("memory_builder.discovery.social_profiles.get_scrapfly_key", return_value="test-key")
    def test_discover_facebook_profile_posts(self, _mock_key, mock_run_async) -> None:
        mock_run_async.return_value = [
            {
                "post_id": "914955354947975",
                "text": "Solve rich people’s problems.",
                "wwwURL": "https://www.facebook.com/reel/27070999992600212/",
                "actors": [{"name": "Alex Hormozi"}],
            }
        ]
        records = discover_social_sources(
            "hormozi",
            [
                {
                    "platform": "facebook",
                    "username": "ahormozi",
                    "url": "https://www.facebook.com/ahormozi/",
                    "max_posts": 5,
                }
            ],
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_url, "https://facebook.com/reel/27070999992600212")
        self.assertEqual(records[0].source_type, SourceType.SOCIAL)


if __name__ == "__main__":
    unittest.main()
