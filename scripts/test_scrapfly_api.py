#!/usr/bin/env python3
"""Live Scrapfly API smoke test for X/Instagram social scraping.

Usage:
    export SCRAPFLY_KEY="..."
    python3 scripts/test_scrapfly_api.py
    python3 scripts/test_scrapfly_api.py --platform instagram
    python3 scripts/test_scrapfly_api.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.env import load_project_env

load_project_env()

from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_client import get_scrapfly_key
from memory_builder.fetch.scrapfly_instagram import scrape_user
from memory_builder.fetch.scrapfly_twitter import format_tweet_text, scrape_profile_tweets, scrape_tweet


# Stable public targets (same URLs as secret-project/scrapfly-scrapers tests)
X_TWEET_URL = "https://x.com/robinhanson/status/1872047986873885082"
X_PROFILE_URL = "https://x.com/alexhormozi"
INSTAGRAM_USERNAME = "instagram"


def test_scrapfly_key() -> None:
    key = get_scrapfly_key()
    masked = key[:6] + "..." + key[-4:] if len(key) > 12 else "(set)"
    print(f"OK  SCRAPFLY_KEY loaded: {masked}")


def test_x_tweet() -> None:
    print(f"\n→ X tweet scrape: {X_TWEET_URL}")
    tweet = run_async(scrape_tweet(X_TWEET_URL))
    text = format_tweet_text(tweet)
    if not tweet.get("id"):
        raise RuntimeError("Tweet response missing id")
    if not tweet.get("text"):
        raise RuntimeError("Tweet response missing text")
    print(f"OK  tweet id={tweet['id']}")
    print(f"    author=@{tweet.get('user', {}).get('screen_name', '?')}")
    preview = text.replace("\n", " ")[:120]
    print(f"    preview: {preview}...")


def test_x_profile_timeline(max_posts: int = 3) -> None:
    print(f"\n→ X profile timeline ({max_posts} posts): {X_PROFILE_URL}")
    tweets = run_async(scrape_profile_tweets(X_PROFILE_URL, max_posts=max_posts))
    if not tweets:
        raise RuntimeError("Profile timeline returned no tweets")
    print(f"OK  fetched {len(tweets)} tweet(s)")
    for tweet in tweets[:3]:
        user = tweet.get("user", {}).get("screen_name", "?")
        snippet = (tweet.get("text") or "(text fetched on process)")[:80].replace("\n", " ")
        print(f"    - @{user} /status/{tweet['id']}: {snippet}...")


def test_api_connectivity() -> None:
    """Lightweight Scrapfly call — confirms key + billing without X DOM fragility."""
    print("\n→ API connectivity (Instagram profile lookup)")
    profile = run_async(scrape_user(INSTAGRAM_USERNAME))
    if not profile.get("username"):
        raise RuntimeError("Scrapfly returned empty Instagram profile")
    print(f"OK  Scrapfly API reachable (@{profile['username']}, followers={profile.get('followers', '?')})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrapfly API smoke test")
    parser.add_argument(
        "--platform",
        choices=("x", "instagram"),
        help="Run only one platform (default: x tweet + timeline)",
    )
    parser.add_argument("--all", action="store_true", help="Run X and Instagram checks")
    parser.add_argument("--include-x", action="store_true", help="Also run X scrape tests (fragile — X DOM changes often)")
    parser.add_argument("--max-posts", type=int, default=3, help="Profile timeline limit")
    args = parser.parse_args()

    print("Scrapfly API smoke test")
    print("=" * 40)

    try:
        test_scrapfly_key()
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    run_x = args.include_x or args.all or args.platform == "x"
    run_ig = args.all or args.platform == "instagram" or args.platform is None

    failures: list[str] = []

    if run_ig or args.platform is None:
        try:
            test_api_connectivity()
        except Exception as exc:
            failures.append(f"API connectivity: {exc}")
            print(f"FAIL API connectivity: {exc}", file=sys.stderr)

    if run_x or args.platform is None:
        for name, fn in (
            ("X tweet", test_x_tweet),
            ("X profile timeline", lambda: test_x_profile_timeline(args.max_posts)),
        ):
            try:
                fn()
            except Exception as exc:
                failures.append(f"{name}: {exc}")
                print(f"FAIL {name}: {exc}", file=sys.stderr)

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED ({len(failures)} check(s))")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
