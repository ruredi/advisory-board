"""Live Scrapfly API integration tests — skipped unless SCRAPFLY_LIVE_TEST=1."""

from __future__ import annotations

import os
import unittest

from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_twitter import scrape_tweet


LIVE = os.environ.get("SCRAPFLY_LIVE_TEST") == "1"
HAS_KEY = bool(os.environ.get("SCRAPFLY_KEY", "").strip())

X_TWEET_URL = "https://x.com/robinhanson/status/1872047986873885082"


@unittest.skipUnless(LIVE and HAS_KEY, "Set SCRAPFLY_KEY and SCRAPFLY_LIVE_TEST=1 to run live Scrapfly tests")
class ScrapflyLiveApiTests(unittest.TestCase):
    def test_scrape_x_tweet(self) -> None:
        tweet = run_async(scrape_tweet(X_TWEET_URL))
        self.assertTrue(tweet.get("id"))
        self.assertTrue(tweet.get("text"))
        self.assertIn("user", tweet)


if __name__ == "__main__":
    unittest.main()
