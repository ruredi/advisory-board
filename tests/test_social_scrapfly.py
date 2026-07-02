from __future__ import annotations

import unittest
from unittest.mock import patch

from memory_builder.discovery.seed_links import (
    classify_source_type,
    is_processable_source,
    is_social_post_url,
    is_social_profile_url,
)
from memory_builder.discovery.social_profiles import discover_social_sources
from memory_builder.fetch.scrapfly_twitter import (
    extract_status_ids,
    find_quoted_status_refs,
    format_tweet_text,
    tweet_public_url,
    _attach_quoted_from_html,
    _parse_tweet_from_html,
)
from memory_builder.models import SourceType


class SocialUrlClassificationTests(unittest.TestCase):
    def test_x_post_url_is_processable(self) -> None:
        url = "https://x.com/alexhormozi/status/1234567890"
        self.assertTrue(is_social_post_url(url))
        self.assertEqual(classify_source_type(url), SourceType.SOCIAL)
        self.assertTrue(is_processable_source(url))

    def test_x_profile_url_is_not_seed_processable(self) -> None:
        url = "https://x.com/alexhormozi"
        self.assertTrue(is_social_profile_url(url))
        self.assertFalse(is_processable_source(url))

    def test_instagram_post_url_is_processable(self) -> None:
        url = "https://www.instagram.com/p/ABC123/"
        self.assertTrue(is_social_post_url(url))
        self.assertTrue(is_processable_source(url))

    def test_instagram_profile_url_is_not_seed_processable(self) -> None:
        url = "https://www.instagram.com/hormozi/"
        self.assertTrue(is_social_profile_url(url))
        self.assertFalse(is_processable_source(url))

    def test_threadreader_thread_is_web(self) -> None:
        url = "https://threadreaderapp.com/thread/1234567890.html"
        self.assertEqual(classify_source_type(url), SourceType.WEB)
        self.assertTrue(is_processable_source(url))


class SocialDiscoveryTests(unittest.TestCase):
    @patch("memory_builder.discovery.social_profiles.run_async")
    @patch("memory_builder.discovery.social_profiles.get_scrapfly_key", return_value="test-key")
    def test_discover_x_profile_posts(self, _mock_key, mock_run_async) -> None:
        mock_run_async.return_value = [
            {
                "id": "111",
                "text": "Offer is the problem.",
                "user": {"screen_name": "alexhormozi"},
            }
        ]
        records = discover_social_sources(
            "hormozi",
            [{"platform": "x", "username": "alexhormozi", "max_posts": 5}],
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source_url, "https://x.com/alexhormozi/status/111")
        self.assertEqual(records[0].source_type, SourceType.SOCIAL)

    @patch("memory_builder.discovery.social_profiles.get_scrapfly_key")
    def test_skips_discovery_without_scrapfly_key(self, mock_key) -> None:
        mock_key.side_effect = RuntimeError("missing key")
        records = discover_social_sources(
            "hormozi",
            [{"platform": "x", "username": "alexhormozi"}],
        )
        self.assertEqual(records, [])

    @patch("memory_builder.discovery.social_profiles.run_async")
    @patch("memory_builder.discovery.social_profiles.get_scrapfly_key", return_value="test-key")
    def test_only_platform_skips_non_matching_profiles(self, _mock_key, mock_run_async) -> None:
        mock_run_async.return_value = [{"shortcode": "ABC123"}]
        records = discover_social_sources(
            "hormozi",
            [
                {"platform": "x", "username": "alexhormozi", "max_posts": 5},
                {"platform": "instagram", "username": "hormozi", "max_posts": 5},
            ],
            only_platform="instagram",
        )
        self.assertEqual(len(records), 1)
        self.assertIn("instagram.com", records[0].source_url)
        mock_run_async.assert_called_once()

    @patch("memory_builder.discovery.social_profiles.run_async")
    @patch("memory_builder.discovery.social_profiles.get_scrapfly_key", return_value="test-key")
    def test_only_platform_x_accepts_twitter_alias(self, _mock_key, mock_run_async) -> None:
        mock_run_async.return_value = [
            {
                "id": "111",
                "text": "Offer is the problem.",
                "user": {"screen_name": "alexhormozi"},
            }
        ]
        records = discover_social_sources(
            "hormozi",
            [{"platform": "twitter", "username": "alexhormozi", "max_posts": 5}],
            only_platform="x",
        )
        self.assertEqual(len(records), 1)
        self.assertIn("x.com", records[0].source_url)


class SocialFormattingTests(unittest.TestCase):
    def test_parse_tweet_from_html(self) -> None:
        html_page = (
            '<meta property="og:description" content="Raise prices when demand exceeds capacity.">'
            '<meta property="og:title" content="Alex Hormozi (@alexhormozi) on X">'
        )
        tweet = _parse_tweet_from_html(
            "https://x.com/alexhormozi/status/1872047986873885082",
            html_page,
        )
        self.assertEqual(tweet["id"], "1872047986873885082")
        self.assertEqual(tweet["text"], "Raise prices when demand exceeds capacity.")
        self.assertEqual(tweet["user"]["screen_name"], "alexhormozi")

    def test_extract_status_ids(self) -> None:
        page = (
            'href="/alexhormozi/status/1872047986873885082">'
            'href="/alexhormozi/status/1969872095137222981">'
            'href="/alexhormozi/status/1872047986873885082">'
        )
        self.assertEqual(
            extract_status_ids(page, 10),
            ["1872047986873885082", "1969872095137222981"],
        )

    def test_find_quoted_status_refs(self) -> None:
        page = (
            'href="/elonmusk/status/2072034905299563005">'
            'href="/neuralink/status/2072026718467166512">'
        )
        refs = find_quoted_status_refs(page, "2072034905299563005")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["screen_name"], "neuralink")
        self.assertEqual(refs[0]["id"], "2072026718467166512")

    def test_attach_quoted_from_html(self) -> None:
        page = (
            '<meta property="og:description" content="Neuralink breakthrough!">'
            '<meta property="og:title" content="Elon Musk (@elonmusk) on X">'
            'href="/neuralink/status/2072026718467166512">'
            '@neuralink The dura is the brain&#39;s armor and we kept it intact. Show more'
        )
        tweet = _parse_tweet_from_html(
            "https://x.com/elonmusk/status/2072034905299563005",
            page,
        )
        tweet = _attach_quoted_from_html(tweet, page)
        self.assertTrue(tweet["is_quote"])
        quoted = tweet["quoted_tweet"]
        self.assertEqual(quoted["id"], "2072026718467166512")
        self.assertIn("dura is the brain", quoted["text"])

    def test_format_tweet_text_with_quote(self) -> None:
        tweet = {
            "id": "2072034905299563005",
            "text": "Neuralink has solved through-dura electrode implantation!",
            "user": {"screen_name": "elonmusk"},
            "quoted_tweet": {
                "id": "2072026718467166512",
                "url": "https://x.com/neuralink/status/2072026718467166512",
                "text": "The dura is the brain's armor.",
                "user": {"screen_name": "neuralink"},
            },
        }
        text = format_tweet_text(tweet)
        self.assertIn("@elonmusk", text)
        self.assertIn("through-dura", text)
        self.assertIn("Quoting @neuralink", text)
        self.assertIn("brain's armor", text)
        self.assertIn("https://x.com/neuralink/status/2072026718467166512", text)

    def test_format_tweet_text(self) -> None:
        tweet = {
            "id": "111",
            "created_at": "Wed Jan 01 00:00:00 +0000 2025",
            "text": "Raise prices when demand exceeds capacity.",
            "attached_urls": ["https://acquisition.com/offer"],
            "reply_count": 10,
            "retweet_count": 20,
            "favorite_count": 100,
            "views": "5000",
            "user": {"screen_name": "alexhormozi"},
        }
        text = format_tweet_text(tweet)
        self.assertIn("@alexhormozi", text)
        self.assertIn("Raise prices", text)
        self.assertIn("https://acquisition.com/offer", text)

    def test_tweet_public_url(self) -> None:
        url = tweet_public_url({"id": "999", "user": {"screen_name": "alexhormozi"}})
        self.assertEqual(url, "https://x.com/alexhormozi/status/999")


if __name__ == "__main__":
    unittest.main()
