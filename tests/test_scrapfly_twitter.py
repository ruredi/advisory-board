from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from memory_builder.fetch.scrapfly_twitter import (
    _extract_description_from_html,
    _parse_tweet_from_html,
    _parse_tweet_from_xhr,
    parse_tweet,
)


def _xhr_result(body: dict) -> SimpleNamespace:
    return SimpleNamespace(
        scrape_result={
            "browser_data": {
                "xhr_call": [
                    {
                        "url": "https://x.com/i/api/graphql/TweetResultByRestId",
                        "response": {"body": json.dumps(body)},
                    }
                ]
            }
        }
    )


class ScrapflyTwitterParseTests(unittest.TestCase):
    def test_parse_tweet_from_xhr(self) -> None:
        payload = {
            "data": {
                "tweetResult": {
                    "result": {
                        "legacy": {
                            "created_at": "Thu Jun 01 13:47:03 +0000 2023",
                            "full_text": "Hello world",
                            "favorite_count": 8,
                            "retweet_count": 1,
                            "reply_count": 7,
                            "quote_count": 0,
                            "bookmark_count": 1,
                            "lang": "en",
                            "user_id_str": "123",
                            "id_str": "1664267318053179398",
                            "conversation_id_str": "1664267318053179398",
                        },
                        "core": {
                            "user_results": {
                                "result": {
                                    "id": "VXNlcjox",
                                    "rest_id": "123",
                                    "is_blue_verified": True,
                                    "legacy": {"screen_name": "alexhormozi", "name": "Alex Hormozi"},
                                }
                            }
                        },
                        "views": {"count": "2296"},
                    }
                }
            }
        }
        tweet = _parse_tweet_from_xhr(_xhr_result(payload))
        self.assertIsNotNone(tweet)
        assert tweet is not None
        self.assertEqual(tweet["text"], "Hello world")
        self.assertEqual(tweet["id"], "1664267318053179398")
        self.assertEqual(tweet["user"]["screen_name"], "alexhormozi")

    def test_parse_tweet_from_html_twitter_description(self) -> None:
        html = """
        <html><head>
        <meta name="twitter:description" content="Scale your business." />
        </head><body></body></html>
        """
        text = _extract_description_from_html(html)
        self.assertEqual(text, "Scale your business.")

    def test_parse_tweet_from_html_json_ld(self) -> None:
        html = """
        <script type="application/ld+json">{"@type":"SocialMediaPosting","articleBody":"Offer math works."}</script>
        """
        tweet = _parse_tweet_from_html("https://x.com/alexhormozi/status/1234567890123456789", html)
        self.assertEqual(tweet["text"], "Offer math works.")

    def test_parse_tweet_visibility_wrapper(self) -> None:
        inner = parse_tweet(
            {
                "legacy": {
                    "full_text": "Wrapped tweet",
                    "id_str": "999",
                    "conversation_id_str": "999",
                    "favorite_count": 0,
                    "retweet_count": 0,
                    "reply_count": 0,
                    "quote_count": 0,
                    "bookmark_count": 0,
                    "lang": "en",
                    "user_id_str": "1",
                }
            }
        )
        self.assertEqual(inner["text"], "Wrapped tweet")


if __name__ == "__main__":
    unittest.main()
