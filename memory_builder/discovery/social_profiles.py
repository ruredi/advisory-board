from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from memory_builder.discovery.seed_links import classify_source_type, infer_source_nature
from memory_builder.discovery.source_emit import OnSourceRecord, emit_source_record
from memory_builder.discovery.watermarks import bootstrap_profile_floor_watermark, bootstrap_profile_watermark, parse_twitter_created_at, parse_unix_timestamp
from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_client import get_scrapfly_key
from memory_builder.fetch.scrapfly_facebook import collect_facebook_posts, facebook_post_public_url
from memory_builder.fetch.scrapfly_instagram import discover_instagram_posts, instagram_post_url
from memory_builder.fetch.scrapfly_twitter import scrape_profile_tweets_since, tweet_public_url
from memory_builder.models import SourceRecord, SourceStatus
from memory_builder.pipeline.platform_filter import social_profile_matches_filter
from memory_builder.storage.sqlite_store import normalize_url
from memory_builder.telemetry.discovery_events import discovery_log

if TYPE_CHECKING:
    from memory_builder.storage.sqlite_store import SQLiteStore


log = logging.getLogger(__name__)

DEFAULT_MAX_PAGES = 50


def _effective_max_pages(limit: int | None, config_max: int) -> int:
    if limit is None or limit <= 0:
        return max(config_max, 500)
    return max(config_max, (limit // 12) + 30)


def _remaining_limit(discovery_limit: int | None, collected: int) -> int | None:
    if discovery_limit is None or discovery_limit <= 0:
        return None
    return max(0, discovery_limit - collected)


def _profile_channel_url(platform: str, username: str, profile_url: str) -> str:
    if profile_url:
        return profile_url.rstrip("/")
    if platform == "instagram":
        return f"https://instagram.com/{username}"
    if platform in {"x", "twitter"}:
        return f"https://x.com/{username}"
    if platform == "facebook":
        return f"https://www.facebook.com/{username}/"
    return profile_url or username


def _instagram_title(post: dict) -> str:
    caption = post.get("caption")
    if isinstance(caption, dict):
        return str(caption.get("text") or "")[:200]
    if isinstance(caption, str) and caption.strip():
        return caption.strip()[:200]
    shortcode = post.get("shortcode")
    return f"Instagram post {shortcode}" if shortcode else "Instagram post"


def discover_social_sources(
    persona_id: str,
    social_profiles: list[dict[str, str | int]],
    *,
    only_platform: str | None = None,
    store: SQLiteStore | None = None,
    discovery_limit: int | None = None,
    on_record: OnSourceRecord | None = None,
    collected_count: Callable[[], int] | None = None,
) -> list[SourceRecord]:
    if not social_profiles:
        return []

    try:
        get_scrapfly_key()
    except RuntimeError:
        discovery_log("Scrapfly API kulcs hiányzik — social keresés kihagyva")
        log.warning("SCRAPFLY_KEY not set — skipping social profile discovery")
        return []

    discovered: list[SourceRecord] = []
    seen: set[str] = set()

    def try_add(record: SourceRecord) -> bool:
        post_url = normalize_url(record.source_url)
        if post_url in seen:
            return True
        seen.add(post_url)
        if on_record is not None:
            return emit_source_record(discovered, record, on_record=on_record)
        if store and not store.source_url_is_new(post_url):
            return True
        discovered.append(record)
        if limit_reached():
            return False
        return True

    def limit_reached() -> bool:
        if on_record is not None:
            return False
        return discovery_limit is not None and discovery_limit > 0 and len(discovered) >= discovery_limit

    def total_collected() -> int:
        if collected_count is not None:
            return collected_count()
        return len(discovered)

    for profile in social_profiles:
        platform = str(profile.get("platform", "")).lower()
        if not social_profile_matches_filter(platform, only_platform):
            continue
        username = str(profile.get("username", "")).strip().lstrip("@")
        profile_url = str(profile.get("url", "")).strip()
        max_pages = int(profile.get("discovery_max_pages", profile.get("max_pages", DEFAULT_MAX_PAGES)))
        if not username and not profile_url:
            continue

        profile_channel = _profile_channel_url(platform, username, profile_url)
        forward_watermark = bootstrap_profile_watermark(store, profile_channel, platform=platform)
        backward_floor = bootstrap_profile_floor_watermark(store, profile_channel, platform=platform)
        known_urls: set[str] = set()
        if store:
            known_urls = store.list_source_urls_for_channel(profile_channel)
            if not known_urls and platform in {"instagram", "x", "twitter", "facebook"}:
                platform_key = "x" if platform in {"x", "twitter"} else platform
                known_urls = store.list_source_urls_for_platform(platform_key)

        handle = username or profile_url
        forward_label = forward_watermark[:10] if forward_watermark else "nincs"
        backward_label = backward_floor[:10] if backward_floor else "nincs"
        profile_limit = _remaining_limit(discovery_limit, total_collected())
        if profile_limit == 0:
            discovery_log(f"{platform.upper()} @{handle}: elértük a keresési limitet, kihagyva")
            continue
        discovery_log(
            f"{platform.upper()} @{handle}: keresés (újabb: {forward_label}, régebbi: {backward_label})",
            metadata={
                "platform": platform,
                "username": username,
                "forward_watermark": forward_watermark,
                "backward_floor": backward_floor,
                "limit": profile_limit,
            },
        )

        try:
            if platform in {"x", "twitter"}:
                url = profile_url or f"https://x.com/{username}"
                tweets = run_async(
                    scrape_profile_tweets_since(
                        url,
                        since_iso=forward_watermark,
                        known_urls=known_urls or None,
                        max_posts=profile_limit or 200,
                    )
                )
                for tweet in tweets:
                    post_url = normalize_url(tweet_public_url(tweet))
                    source_date = parse_twitter_created_at(tweet.get("created_at"))
                    if not try_add(
                        _social_source_record(
                            persona_id,
                            post_url,
                            channel_url=profile_channel,
                            source_date=source_date,
                            source_title=(tweet.get("text") or post_url)[:200],
                        )
                    ):
                        break
                    if limit_reached():
                        break
            elif platform == "instagram":
                page_limit = _effective_max_pages(profile_limit, max_pages)

                def handle_instagram_post(post: dict) -> bool:
                    shortcode = post.get("shortcode")
                    if not shortcode:
                        return True
                    post_url = normalize_url(instagram_post_url(str(shortcode)))
                    source_date = parse_unix_timestamp(post.get("taken_at"))
                    if not try_add(
                        _social_source_record(
                            persona_id,
                            post_url,
                            channel_url=profile_channel,
                            source_date=source_date,
                            source_title=_instagram_title(post),
                        )
                    ):
                        return False
                    return True

                before_count = len(discovered)
                if on_record is not None:
                    run_async(
                        discover_instagram_posts(
                            username,
                            forward_since=forward_watermark,
                            backward_before=backward_floor,
                            known_urls=known_urls or None,
                            limit=profile_limit,
                            max_pages=page_limit,
                            on_post=handle_instagram_post,
                        )
                    )
                    discovery_log(f"Instagram @{username}: keresés kész")
                else:
                    posts = run_async(
                        discover_instagram_posts(
                            username,
                            forward_since=forward_watermark,
                            backward_before=backward_floor,
                            known_urls=known_urls or None,
                            limit=profile_limit,
                            max_pages=page_limit,
                        )
                    )
                    for post in posts:
                        if not handle_instagram_post(post):
                            break
                    discovery_log(f"Instagram @{username}: {len(discovered) - before_count} új forrás URL")
            elif platform == "facebook":
                url = profile_url or f"https://www.facebook.com/{username}/"
                posts = run_async(
                    collect_facebook_posts(url, known_urls=known_urls or None, max_posts=200)
                )
                for post in posts:
                    post_url = normalize_url(facebook_post_public_url(post, url))
                    if not try_add(
                        _social_source_record(
                            persona_id,
                            post_url,
                            channel_url=profile_channel,
                            source_title=str(post.get("text") or post_url)[:200],
                        )
                    ):
                        break
                    if limit_reached():
                        break
            else:
                discovery_log(f"Ismeretlen platform kihagyva: {platform} ({profile_url or username})")
                log.warning("Skipping unsupported social profile platform: %s (%s)", platform, profile_url or username)
        except Exception as exc:
            message = str(exc)
            discovery_log(f"{platform.upper()} @{handle}: hiba — {message}")
            log.warning(
                "Social discovery failed for %s (%s): %s",
                platform,
                profile_url or username,
                exc,
            )
            if "kvóta" in message.lower() or "quota" in message.lower():
                discovery_log("Scrapfly kvóta miatt a többi social profil kihagyva")
                break
            continue

    if on_record is None:
        discovery_log(f"Social: összesen {len(discovered)} új forrás")
    else:
        discovery_log("Social: keresés kész")
    return discovered


def _social_source_record(
    persona_id: str,
    post_url: str,
    *,
    channel_url: str,
    source_date: str | None = None,
    source_title: str | None = None,
) -> SourceRecord:
    source_type = classify_source_type(post_url)
    return SourceRecord(
        persona_id=persona_id,
        source_url=post_url,
        source_title=source_title or post_url,
        source_type=source_type,
        source_date=source_date,
        source_nature=infer_source_nature(source_type, post_url),
        status=SourceStatus.PENDING,
        channel_url=channel_url,
    )
