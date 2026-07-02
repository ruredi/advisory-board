"""X.com (Twitter) scraping via Scrapfly.

Uses rendered page metadata when GraphQL XHR interception is blocked by X.
Adapted from secret-project/scrapfly-scrapers/twitter-scraper with 2026 fallback.
"""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

import jmespath
from scrapfly import ScrapeConfig

from memory_builder.fetch.scrapfly_client import get_scrapfly_client
from memory_builder.telemetry.usage_helpers import maybe_record_scrapfly


log = logging.getLogger(__name__)

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "session_sticky_proxy": False,
}
STATUS_ID_PATTERN = re.compile(r"/status/(\d{10,25})")
STATUS_LINK_PATTERN = re.compile(
    r'href="(?:https?://(?:www\.)?(?:x|twitter)\.com)?/([A-Za-z0-9_]+)/status/(\d{10,25})"',
    re.IGNORECASE,
)
OG_DESCRIPTION_PATTERN = re.compile(r'<meta property="og:description" content="([^"]*)"', re.IGNORECASE)
TWITTER_DESCRIPTION_PATTERN = re.compile(
    r'<meta (?:name|property)="twitter:description" content="([^"]*)"',
    re.IGNORECASE,
)
OG_TITLE_PATTERN = re.compile(r'<meta property="og:title" content="([^"]*)"', re.IGNORECASE)
TWEET_TEXT_HTML_PATTERN = re.compile(
    r'data-testid="tweetText"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
TWEET_XHR_URL_MARKERS = (
    "TweetResultByRestId",
    "TweetDetail",
    "TweetResultByRestIdQuery",
    "TweetResultByRestIdQueryV2",
)
SCREEN_NAME_FROM_OG_TITLE = re.compile(r"\(@([A-Za-z0-9_]+)\)")
JSON_LD_SOCIAL_POSTING = re.compile(
    r'<script type="application/ld\+json"[^>]*>(\{[^<]*"@type"\s*:\s*"SocialMediaPosting"[^<]*\})</script>',
    re.IGNORECASE | re.DOTALL,
)
RESERVED_X_PATHS = frozenset({"home", "search", "explore", "i", "intent", "share", "hashtag"})
TRUNCATED_QUOTE_MARKERS = ("show more", "…", "...")


async def _scrape_twitter_page(url: str, _retries: int = 0, **scrape_config: Any) -> Any:
    if not _retries:
        log.info("scraping %s", url)
    else:
        log.info("retrying %s/2 %s", _retries, url)
    client = get_scrapfly_client()
    result = await client.async_scrape(
        ScrapeConfig(url, lang=["en-US"], auto_scroll=True, **scrape_config, **BASE_CONFIG)
    )
    maybe_record_scrapfly(result, operation="twitter_scrape", metadata={"url": url})
    if result.status_code == 429:
        raise RuntimeError(f"Scrapfly/X rate limited (429) for {url}. Retry later.")
    content = result.content or ""
    xhr_calls = result.scrape_result.get("browser_data", {}).get("xhr_call", [])
    if not content and not xhr_calls:
        raise RuntimeError(
            f"Empty Twitter scrape response for {url} (status={result.status_code}). "
            "Check SCRAPFLY_KEY quota or retry later."
        )
    if "Something went wrong, but" in content:
        if _retries > 2:
            raise RuntimeError("Twitter web app crashed too many times")
        return await _scrape_twitter_page(url, _retries=_retries + 1, **scrape_config)
    return result


def parse_profile(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data["id"],
        "rest_id": data["rest_id"],
        "verified": data["is_blue_verified"],
        **data["legacy"],
    }


def parse_tweet(data: dict[str, Any]) -> dict[str, Any]:
    result = jmespath.search(
        """{
        created_at: legacy.created_at,
        attached_urls: legacy.entities.urls[].expanded_url,
        attached_urls2: legacy.entities.url.urls[].expanded_url,
        attached_media: legacy.entities.media[].media_url_https,
        tagged_users: legacy.entities.user_mentions[].screen_name,
        tagged_hashtags: legacy.entities.hashtags[].text,
        favorite_count: legacy.favorite_count,
        bookmark_count: legacy.bookmark_count,
        quote_count: legacy.quote_count,
        reply_count: legacy.reply_count,
        retweet_count: legacy.retweet_count,
        text: legacy.full_text,
        is_quote: legacy.is_quote_status,
        is_retweet: legacy.retweeted,
        language: legacy.lang,
        user_id: legacy.user_id_str,
        id: legacy.id_str,
        conversation_id: legacy.conversation_id_str,
        source: source,
        views: views.count
    }""",
        data,
    )
    result["poll"] = {}
    poll_data = jmespath.search("card.legacy.binding_values", data) or []
    for poll_entry in poll_data:
        key, value = poll_entry["key"], poll_entry["value"]
        if "choice" in key:
            result["poll"][key] = value["string_value"]
        elif "end_datetime" in key:
            result["poll"]["end"] = value["string_value"]
        elif "last_updated_datetime" in key:
            result["poll"]["updated"] = value["string_value"]
        elif "counts_are_final" in key:
            result["poll"]["ended"] = value["boolean_value"]
        elif "duration_minutes" in key:
            result["poll"]["duration"] = value["string_value"]
    user_data = jmespath.search("core.user_results.result", data)
    if user_data:
        result["user"] = parse_profile(user_data)
    quoted_data = jmespath.search("quoted_status_result.result", data)
    if quoted_data:
        result["is_quote"] = True
        result["quoted_tweet"] = _parse_nested_tweet(quoted_data)
    return result


def _unwrap_tweet_result(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("__typename") == "TweetWithVisibilityResults":
        inner = data.get("tweet")
        if isinstance(inner, dict):
            return inner
    return data


def _parse_nested_tweet(data: dict[str, Any]) -> dict[str, Any]:
    data = _unwrap_tweet_result(data)
    if "legacy" not in data:
        return {}
    parsed = parse_tweet(data)
    screen_name = (parsed.get("user") or {}).get("screen_name") or "i/web"
    tweet_id = parsed.get("id") or ""
    parsed["url"] = f"https://x.com/{screen_name}/status/{tweet_id}" if tweet_id else None
    return parsed


def _extract_timeline_tweets(data: dict[str, Any]) -> list[dict[str, Any]]:
    tweets: list[dict[str, Any]] = []
    instructions = jmespath.search(
        "data.user.result.timeline_v2.timeline.instructions[] | data.user.result.timeline.timeline.instructions[]",
        data,
    ) or []
    if not isinstance(instructions, list):
        instructions = [instructions]
    entries: list[Any] = []
    for instruction in instructions:
        if isinstance(instruction, dict):
            entries.extend(instruction.get("entries") or [])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("entryId", "")
        if entry_id.startswith("promoted-"):
            continue
        result = jmespath.search("content.itemContent.tweet_results.result", entry)
        if not result:
            result = jmespath.search("content.tweetResult.result", entry)
        if not result or not isinstance(result, dict):
            continue
        if result.get("__typename") == "TweetWithVisibilityResults":
            result = result.get("tweet") or result
        if "legacy" not in result:
            continue
        tweets.append(parse_tweet(result))
    return tweets


def _parse_tweet_from_xhr(result: Any) -> dict[str, Any] | None:
    xhr_calls = result.scrape_result.get("browser_data", {}).get("xhr_call", [])
    tweet_calls = [
        item
        for item in xhr_calls
        if any(marker in item.get("url", "") for marker in TWEET_XHR_URL_MARKERS)
    ]
    for xhr in tweet_calls:
        if not xhr.get("response"):
            continue
        try:
            data = json.loads(xhr["response"]["body"])
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
        tweet_result = jmespath.search("data.tweetResult.result", data)
        if not isinstance(tweet_result, dict):
            continue
        tweet_result = _unwrap_tweet_result(tweet_result)
        if "legacy" not in tweet_result:
            continue
        return parse_tweet(tweet_result)
    return None


def _extract_description_from_html(page_html: str) -> str | None:
    for pattern in (TWITTER_DESCRIPTION_PATTERN, OG_DESCRIPTION_PATTERN):
        match = pattern.search(page_html)
        if match:
            text = html.unescape(match.group(1)).strip()
            if text:
                return text
    for match in JSON_LD_SOCIAL_POSTING.finditer(page_html):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        for key in ("articleBody", "description", "headline"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    tweet_text_match = TWEET_TEXT_HTML_PATTERN.search(page_html)
    if tweet_text_match:
        text = _html_to_plain(tweet_text_match.group(1))
        if text:
            return text
    return None


def _screen_name_from_url(url: str) -> str | None:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if len(path_parts) >= 1 and path_parts[0] not in {"i", "home", "search", "explore"}:
        return path_parts[0]
    return None


def _status_id_from_url(url: str) -> str | None:
    match = STATUS_ID_PATTERN.search(url)
    return match.group(1) if match else None


def _html_to_plain(fragment: str) -> str:
    without_scripts = re.sub(r"<script[^>]*>.*?</script>", " ", fragment, flags=re.IGNORECASE | re.DOTALL)
    without_styles = re.sub(r"<style[^>]*>.*?</style>", " ", without_scripts, flags=re.IGNORECASE | re.DOTALL)
    plain = re.sub(r"<[^>]+>", " ", without_styles)
    plain = html.unescape(plain)
    return re.sub(r"\s+", " ", plain).strip()


def find_quoted_status_refs(page_html: str, main_tweet_id: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for match in STATUS_LINK_PATTERN.finditer(page_html):
        screen_name = match.group(1)
        tweet_id = match.group(2)
        if screen_name.lower() in RESERVED_X_PATHS:
            continue
        if tweet_id == main_tweet_id or tweet_id in seen_ids:
            continue
        seen_ids.add(tweet_id)
        refs.append(
            {
                "screen_name": screen_name,
                "id": tweet_id,
                "url": f"https://x.com/{screen_name}/status/{tweet_id}",
            }
        )
    return refs


def _extract_inline_quoted_text(page_html: str, quoted_screen_name: str, main_text: str) -> str | None:
    link_needle = f"/{quoted_screen_name}/status/"
    start = page_html.lower().find(link_needle.lower())
    if start < 0:
        return None

    chunk = page_html[start : start + 12_000]
    plain = _html_to_plain(chunk)
    handle = f"@{quoted_screen_name}"

    candidates: list[str] = []
    for match in re.finditer(rf"{re.escape(handle)}\s*(.*?)(?:Show more|Read \d[\d,]* replies|$)", plain, re.IGNORECASE):
        snippet = match.group(1).strip(" ·|-")
        snippet = re.sub(r"^[A-Z][a-z]{2}\s+\d{1,2}\s+", "", snippet)
        snippet = re.sub(r"^\d{1,2}\s+[A-Z][a-z]{2}\s+", "", snippet)
        if snippet:
            candidates.append(snippet)

    normalized_main = re.sub(r"\s+", " ", main_text.strip())
    for candidate in candidates:
        normalized = re.sub(r"\s+", " ", candidate.strip())
        if not normalized or normalized == normalized_main:
            continue
        if normalized_main and normalized_main in normalized:
            continue
        return candidate.strip()

    # Fallback: longest distinct paragraph after the quoted handle.
    handle_idx = plain.lower().find(handle.lower())
    if handle_idx >= 0:
        tail = plain[handle_idx + len(handle) :].strip(" ·|-")
        if tail and tail != normalized_main and normalized_main not in tail:
            trimmed = re.split(r"Show more|Read \d", tail, maxsplit=1)[0].strip()
            if len(trimmed) >= 40:
                return trimmed
    return None


def _looks_truncated(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return True
    if len(lowered) < 80:
        return True
    if lowered.endswith(TRUNCATED_QUOTE_MARKERS):
        return True
    if re.search(r"here['\u2019]s\s*$", lowered):
        return True
    if "show more" in lowered:
        return True
    return False


def _attach_quoted_from_html(tweet: dict[str, Any], page_html: str) -> dict[str, Any]:
    if tweet.get("quoted_tweet"):
        tweet["is_quote"] = True
        return tweet

    main_id = str(tweet.get("id") or "")
    refs = find_quoted_status_refs(page_html, main_id)
    if not refs:
        return tweet

    ref = refs[0]
    inline_text = _extract_inline_quoted_text(page_html, ref["screen_name"], tweet.get("text") or "")
    tweet["is_quote"] = True
    tweet["quoted_tweet"] = {
        "id": ref["id"],
        "url": ref["url"],
        "text": inline_text or "",
        "user": {"screen_name": ref["screen_name"]},
    }
    return tweet


async def _fetch_quoted_tweet_body(url: str) -> dict[str, Any]:
    result = await _scrape_twitter_page(url, wait_for_selector='[data-testid="tweet"]')
    tweet = _parse_tweet_from_xhr(result)
    if tweet:
        return tweet
    return _parse_tweet_from_html(url, result.content or "")


async def _enrich_with_quoted_context(tweet: dict[str, Any], page_html: str) -> dict[str, Any]:
    tweet = _attach_quoted_from_html(tweet, page_html)
    quoted = tweet.get("quoted_tweet")
    if not isinstance(quoted, dict):
        return tweet

    quoted_url = quoted.get("url")
    quoted_text = str(quoted.get("text") or "").strip()
    if not quoted_url:
        return tweet

    if not _looks_truncated(quoted_text):
        return tweet

    try:
        fetched = await _fetch_quoted_tweet_body(str(quoted_url))
        fetched_text = str(fetched.get("text") or "").strip()
        if fetched_text:
            quoted["text"] = fetched_text
        fetched_user = fetched.get("user") or {}
        if fetched_user.get("screen_name"):
            quoted["user"] = fetched_user
        if fetched.get("id"):
            quoted["id"] = fetched["id"]
    except Exception as exc:
        log.warning("Could not fetch quoted tweet %s: %s", quoted_url, exc)

    return tweet


def _parse_tweet_from_html(url: str, page_html: str) -> dict[str, Any]:
    tweet_id = _status_id_from_url(url)
    if not tweet_id:
        raise RuntimeError(f"Could not extract tweet id from URL: {url}")

    text = _extract_description_from_html(page_html)
    if not text:
        raise RuntimeError(f"Could not extract tweet text from rendered page: {url}")

    title_match = OG_TITLE_PATTERN.search(page_html)
    screen_name = _screen_name_from_url(url)
    if title_match:
        title_screen = SCREEN_NAME_FROM_OG_TITLE.search(title_match.group(1))
        if title_screen:
            screen_name = title_screen.group(1)

    return {
        "id": tweet_id,
        "text": text,
        "created_at": None,
        "attached_urls": [],
        "attached_media": None,
        "tagged_users": [],
        "tagged_hashtags": [],
        "favorite_count": None,
        "bookmark_count": None,
        "quote_count": None,
        "reply_count": None,
        "retweet_count": None,
        "views": None,
        "is_quote": False,
        "quoted_tweet": None,
        "user": {"screen_name": screen_name or "i/web"},
    }


def extract_status_ids(page_html: str, max_posts: int) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in STATUS_ID_PATTERN.finditer(page_html):
        tweet_id = match.group(1)
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        ordered.append(tweet_id)
        if len(ordered) >= max_posts:
            break
    return ordered


async def scrape_tweet(url: str) -> dict[str, Any]:
    result = await _scrape_twitter_page(url, wait_for_selector='[data-testid="tweet"]')
    page_html = result.content or ""
    tweet = _parse_tweet_from_xhr(result)
    if tweet:
        if not tweet.get("url"):
            screen_name = (tweet.get("user") or {}).get("screen_name") or _screen_name_from_url(url) or "i/web"
            tweet["url"] = f"https://x.com/{screen_name}/status/{tweet['id']}"
        return await _enrich_with_quoted_context(tweet, page_html)
    parsed = _parse_tweet_from_html(url, page_html)
    parsed["url"] = url
    return await _enrich_with_quoted_context(parsed, page_html)


async def scrape_profile(url: str) -> dict[str, Any]:
    result = await _scrape_twitter_page(url, wait_for_selector="xhr:UserTweets")
    xhr_calls = result.scrape_result.get("browser_data", {}).get("xhr_call", [])
    user_calls = [item for item in xhr_calls if "UserBy" in item.get("url", "")]
    for xhr in user_calls:
        if not xhr.get("response"):
            continue
        data = json.loads(xhr["response"]["body"])
        return parse_profile(data["data"]["user"]["result"])

    for xhr in xhr_calls:
        if "UserTweets" not in xhr.get("url", "") or not xhr.get("response"):
            continue
        data = json.loads(xhr["response"]["body"])
        timeline = data.get("data", {}).get("user", {}).get("result", {}).get("timeline", {})
        instructions = timeline.get("timeline", {}).get("instructions", [])
        for instruction in instructions:
            for entry in instruction.get("entries", []):
                item = entry.get("content", {}).get("itemContent", {})
                if item.get("__typename") != "TimelineTweet":
                    continue
                user_result = item["tweet_results"]["result"]["core"]["user_results"]["result"]
                if user_result.get("rest_id"):
                    return parse_profile(user_result)

    screen_name = _screen_name_from_url(url)
    title_match = OG_TITLE_PATTERN.search(result.content or "")
    if title_match:
        title_screen = SCREEN_NAME_FROM_OG_TITLE.search(title_match.group(1))
        if title_screen:
            screen_name = title_screen.group(1)
    if not screen_name:
        raise RuntimeError(f"Failed to scrape user profile: {url}")
    return {
        "id": screen_name,
        "rest_id": "",
        "verified": False,
        "screen_name": screen_name,
        "name": screen_name,
    }


async def scrape_profile_tweets(url: str, max_posts: int = 50) -> list[dict[str, Any]]:
    result = await _scrape_twitter_page(url, wait_for_selector="xhr:UserTweets")
    page_html = result.content or ""
    screen_name = _screen_name_from_url(url) or "i/web"

    tweets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    xhr_calls = result.scrape_result.get("browser_data", {}).get("xhr_call", [])
    tweet_calls = [item for item in xhr_calls if "UserTweets" in item.get("url", "")]
    for xhr in tweet_calls:
        if not xhr.get("response"):
            continue
        try:
            data = json.loads(xhr["response"]["body"])
        except (json.JSONDecodeError, TypeError):
            continue
        for parsed in _extract_timeline_tweets(data):
            tweet_id = parsed.get("id")
            if not tweet_id or tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)
            tweets.append(parsed)
            if len(tweets) >= max_posts:
                return tweets

    for tweet_id in extract_status_ids(page_html, max_posts):
        if tweet_id in seen_ids:
            continue
        seen_ids.add(tweet_id)
        tweets.append(
            {
                "id": tweet_id,
                "text": "",
                "user": {"screen_name": screen_name},
            }
        )

    if not tweets:
        raise RuntimeError(f"Failed to scrape profile tweets: no status links found for {url}")
    return tweets


def tweet_public_url(tweet: dict[str, Any]) -> str:
    user = tweet.get("user") or {}
    screen_name = user.get("screen_name") or "i/web"
    return f"https://x.com/{screen_name}/status/{tweet['id']}"


def format_tweet_text(tweet: dict[str, Any]) -> str:
    lines: list[str] = []
    user = tweet.get("user") or {}
    if user.get("screen_name"):
        lines.append(f"@{user['screen_name']}")
    if tweet.get("created_at"):
        lines.append(str(tweet["created_at"]))
    text = tweet.get("text")
    if text:
        lines.append(str(text))
    attached_urls = tweet.get("attached_urls") or []
    if attached_urls:
        lines.append("")
        lines.append("Links:")
        lines.extend(str(url) for url in attached_urls)

    quoted = tweet.get("quoted_tweet")
    if isinstance(quoted, dict) and (quoted.get("text") or quoted.get("url")):
        quoted_user = quoted.get("user") or {}
        quoted_handle = quoted_user.get("screen_name") or "unknown"
        lines.append("")
        lines.append(f"--- Quoting @{quoted_handle} ---")
        if quoted.get("text"):
            lines.append(str(quoted["text"]))
        if quoted.get("url"):
            lines.append(f"Quoted post: {quoted['url']}")

    metrics = []
    for key, label in (
        ("reply_count", "replies"),
        ("retweet_count", "retweets"),
        ("favorite_count", "likes"),
        ("views", "views"),
    ):
        value = tweet.get(key)
        if value is not None:
            metrics.append(f"{label}: {value}")
    if metrics:
        lines.append("")
        lines.append(" | ".join(metrics))
    return "\n".join(lines).strip()
