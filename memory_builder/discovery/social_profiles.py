from __future__ import annotations

import logging

from memory_builder.discovery.seed_links import classify_source_type, infer_source_nature
from memory_builder.pipeline.platform_filter import social_profile_matches_filter
from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_client import get_scrapfly_key
from memory_builder.fetch.scrapfly_instagram import collect_user_posts, instagram_post_url
from memory_builder.fetch.scrapfly_facebook import collect_facebook_posts, facebook_post_public_url
from memory_builder.fetch.scrapfly_twitter import scrape_profile_tweets, tweet_public_url
from memory_builder.models import SourceRecord, SourceStatus
from memory_builder.storage.sqlite_store import normalize_url


log = logging.getLogger(__name__)


def discover_social_sources(
    persona_id: str,
    social_profiles: list[dict[str, str | int]],
    *,
    only_platform: str | None = None,
) -> list[SourceRecord]:
    if not social_profiles:
        return []

    try:
        get_scrapfly_key()
    except RuntimeError:
        log.warning("SCRAPFLY_KEY not set — skipping social profile discovery")
        return []

    discovered: list[SourceRecord] = []
    seen: set[str] = set()

    for profile in social_profiles:
        platform = str(profile.get("platform", "")).lower()
        if not social_profile_matches_filter(platform, only_platform):
            continue
        username = str(profile.get("username", "")).strip().lstrip("@")
        max_posts = int(profile.get("max_posts", 50))
        profile_url = str(profile.get("url", "")).strip()
        if not username and not profile_url:
            continue

        try:
            if platform in {"x", "twitter"}:
                url = profile_url or f"https://x.com/{username}"
                tweets = run_async(scrape_profile_tweets(url, max_posts=max_posts))
                for tweet in tweets:
                    post_url = normalize_url(tweet_public_url(tweet))
                    if post_url in seen:
                        continue
                    seen.add(post_url)
                    discovered.append(_social_source_record(persona_id, post_url))
            elif platform == "instagram":
                posts = run_async(collect_user_posts(username, max_posts=max_posts))
                for post in posts:
                    shortcode = post.get("shortcode")
                    if not shortcode:
                        continue
                    post_url = normalize_url(instagram_post_url(str(shortcode)))
                    if post_url in seen:
                        continue
                    seen.add(post_url)
                    discovered.append(_social_source_record(persona_id, post_url))
            elif platform == "facebook":
                url = profile_url or f"https://www.facebook.com/{username}/"
                posts = run_async(collect_facebook_posts(url, max_posts=max_posts))
                for post in posts:
                    post_url = normalize_url(facebook_post_public_url(post, url))
                    if post_url in seen:
                        continue
                    seen.add(post_url)
                    discovered.append(_social_source_record(persona_id, post_url))
            else:
                log.warning("Skipping unsupported social profile platform: %s (%s)", platform, profile_url or username)
        except Exception as exc:
            log.warning(
                "Social discovery failed for %s (%s): %s",
                platform,
                profile_url or username,
                exc,
            )
            continue

    return discovered


def _social_source_record(persona_id: str, post_url: str) -> SourceRecord:
    source_type = classify_source_type(post_url)
    return SourceRecord(
        persona_id=persona_id,
        source_url=post_url,
        source_title=post_url,
        source_type=source_type,
        source_nature=infer_source_nature(source_type, post_url),
        status=SourceStatus.PENDING,
    )
