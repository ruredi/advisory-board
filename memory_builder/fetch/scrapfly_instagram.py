"""Instagram scraping via Scrapfly — adapted from secret-project/scrapfly-scrapers/instagram-scraper."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import jmespath
from scrapfly import ScrapeConfig

from memory_builder.fetch.scrapfly_client import get_scrapfly_client, parse_scrapfly_json
from memory_builder.discovery.watermarks import is_newer_than, parse_unix_timestamp
from memory_builder.storage.sqlite_store import normalize_url
from memory_builder.telemetry.discovery_events import discovery_log
from memory_builder.telemetry.usage_helpers import maybe_record_scrapfly


log = logging.getLogger(__name__)

BASE_CONFIG = {
    "asp": True,
    "country": "CA",
}
INSTAGRAM_APP_ID = "936619743392459"
# PolarisPostRootQuery — replaces deprecated xdt_shortcode_media doc_id (8845758582119845).
INSTAGRAM_DOCUMENT_ID = "27128499623469141"
INSTAGRAM_ACCOUNT_DOCUMENT_ID = "9310670392322965"
INSTAGRAM_MEDIA_TYPES = {1: "GraphImage", 2: "GraphVideo", 8: "GraphSidecar"}


def parse_user(data: dict[str, Any]) -> dict[str, Any]:
    return jmespath.search(
        """{
        name: full_name,
        username: username,
        id: id,
        category: category_name,
        bio: biography,
        bio_links: bio_links[].url,
        homepage: external_url,
        followers: edge_followed_by.count,
        follows: edge_follow.count,
        is_private: is_private,
        is_verified: is_verified,
        profile_image: profile_pic_url_hd,
        image_count: edge_owner_to_timeline_media.count
    }""",
        data,
    )


def parse_comments(data: dict[str, Any]) -> dict[str, Any]:
    if "edge_media_to_comment" in data:
        return jmespath.search(
            """{
                comments_count: edge_media_to_comment.count,
                comments_disabled: comments_disabled,
                comments: edge_media_to_comment.edges[].node.{
                    id: id,
                    text: text,
                    created_at: created_at,
                    owner: owner.username
                }
            }""",
            data,
        )
    return jmespath.search(
        """{
            comments_count: edge_media_to_parent_comment.count,
            comments_disabled: comments_disabled,
            comments: edge_media_to_parent_comment.edges[].node.{
                id: id,
                text: text,
                created_at: created_at,
                owner: owner.username
            }
        }""",
        data,
    )


def parse_post(data: dict[str, Any]) -> dict[str, Any]:
    result = jmespath.search(
        """{
        id: id,
        shortcode: shortcode,
        src: display_url,
        video_url: video_url,
        views: video_view_count,
        likes: edge_media_preview_like.count,
        location: location.name,
        taken_at: taken_at_timestamp,
        type: product_type,
        video_duration: video_duration,
        is_video: is_video,
        tagged_users: edge_media_to_tagged_user.edges[].node.user.username,
        captions: edge_media_to_caption.edges[].node.text
    }""",
        data,
    )
    if not isinstance(result, dict):
        shortcode = data.get("shortcode") or data.get("code") or "unknown"
        raise RuntimeError(f"Failed to parse Instagram post payload for shortcode {shortcode}")
    comments = parse_comments(data)
    if isinstance(comments, dict):
        result.update(comments)
    return _attach_carousel_images(data, result)


def _attach_carousel_images(data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if "edge_sidecar_to_children" in data:
        carousel_data = jmespath.search(
            """{
            carousel_count: edge_sidecar_to_children.count,
            images: edge_sidecar_to_children.edges[].node.{
                id: id,
                shortcode: shortcode,
                display_url: display_url,
                is_video: is_video,
                video_url: video_url
            }
        }""",
            data,
        )
        if isinstance(carousel_data, dict):
            carousel_data["is_carousel"] = True
            result.update(carousel_data)
    else:
        result["is_carousel"] = False
        result["carousel_count"] = 1
        result["images"] = [
            {
                "id": result.get("id"),
                "shortcode": result.get("shortcode"),
                "display_url": result.get("src"),
                "is_video": result.get("is_video"),
                "video_url": result.get("video_url"),
            }
        ]
    return result


def parse_user_posts(data: dict[str, Any]) -> dict[str, Any]:
    return jmespath.search(
        """{
        id: id,
        shortcode: code,
        caption: caption,
        taken_at: taken_at,
        link: link,
        title: title,
        comment_count: comment_count,
        like_count: like_count,
        comments: comments
    }""",
        data,
    )


async def scrape_user(username: str) -> dict[str, Any]:
    log.info("scraping instagram user %s", username)
    client = get_scrapfly_client()
    result = await client.async_scrape(
        ScrapeConfig(
            url=f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers={"x-ig-app-id": INSTAGRAM_APP_ID},
            **BASE_CONFIG,
        )
    )
    maybe_record_scrapfly(result, operation="instagram_user", metadata={"username": username})
    data = parse_scrapfly_json(result, operation=f"instagram profile @{username}")
    return parse_user(data["data"]["user"])


async def scrape_post(url_or_shortcode: str) -> dict[str, Any]:
    if "http" in url_or_shortcode:
        shortcode = url_or_shortcode.split("/p/")[-1].split("/reel/")[-1].split("/")[0]
    else:
        shortcode = url_or_shortcode

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return await _scrape_post_once(shortcode)
        except RuntimeError as exc:
            last_error = exc
            if attempt < 2 and _is_retryable_instagram_error(str(exc)):
                delay_seconds = 5 * (attempt + 1)
                log.warning(
                    "Instagram post %s scrape failed (attempt %s/3): %s — retry in %ss",
                    shortcode,
                    attempt + 1,
                    exc,
                    delay_seconds,
                )
                await asyncio.sleep(delay_seconds)
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Instagram post scrape failed for shortcode {shortcode}")


def _is_retryable_instagram_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "execution error",
            "401",
            "unauthorized",
            "rate limit",
            "429",
            "timeout",
            "connection",
            "empty scrape",
        )
    )


def _instagram_post_graphql_variables(shortcode: str) -> str:
    return json.dumps(
        {
            "shortcode": shortcode,
            "__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider": False,
        },
        separators=(",", ":"),
    )


def _extract_post_media_from_graphql(payload: dict[str, Any], *, shortcode: str) -> dict[str, Any]:
    data_block = payload.get("data")
    if not isinstance(data_block, dict):
        detail = _format_instagram_graphql_errors(payload)
        raise RuntimeError(f"Instagram post unavailable for shortcode {shortcode}: {detail}")

    legacy_media = data_block.get("xdt_shortcode_media")
    if isinstance(legacy_media, dict):
        return legacy_media

    web_info = data_block.get("xdt_api__v1__media__shortcode__web_info")
    if isinstance(web_info, dict):
        items = web_info.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            return _convert_v1_media_to_legacy(items[0])

    detail = _format_instagram_graphql_errors(payload)
    raise RuntimeError(f"Instagram post missing media payload for shortcode {shortcode}: {detail}")


def _convert_v1_media_to_legacy(media: dict[str, Any]) -> dict[str, Any]:
    """Map Instagram v1/iPhone API media payload to legacy GraphQL field names."""
    media_type = media.get("media_type")
    typename = INSTAGRAM_MEDIA_TYPES.get(media_type)
    if not typename:
        raise RuntimeError(f"Unknown Instagram media_type in payload: {media_type!r}")

    legacy: dict[str, Any] = {
        "shortcode": media.get("code") or media.get("shortcode"),
        "id": media.get("pk") or media.get("id"),
        "__typename": typename,
        "is_video": media_type == 2,
        "taken_at_timestamp": media.get("taken_at"),
        "product_type": media.get("product_type"),
    }

    candidates = (media.get("image_versions2") or {}).get("candidates") or []
    if candidates and isinstance(candidates[0], dict):
        legacy["display_url"] = candidates[0].get("url")

    video_versions = media.get("video_versions") or []
    if video_versions and isinstance(video_versions[0], dict):
        legacy["video_url"] = video_versions[0].get("url")

    if media.get("video_duration") is not None:
        legacy["video_duration"] = media["video_duration"]
    if media.get("view_count") is not None:
        legacy["video_view_count"] = media["view_count"]
    if media.get("play_count") is not None:
        legacy["video_play_count"] = media["play_count"]

    caption = media.get("caption")
    caption_text = caption.get("text") if isinstance(caption, dict) else None
    legacy["edge_media_to_caption"] = (
        {"edges": [{"node": {"text": caption_text}}]} if caption_text is not None else {"edges": []}
    )
    legacy["edge_media_preview_like"] = {"count": media.get("like_count") or 0}
    legacy["edge_media_to_parent_comment"] = {
        "count": media.get("comment_count") or 0,
        "edges": [],
    }
    if media.get("location"):
        legacy["location"] = media["location"]

    carousel = media.get("carousel_media") or []
    if carousel:
        carousel_nodes: list[dict[str, Any]] = []
        for item in carousel:
            if not isinstance(item, dict):
                continue
            item_type = item.get("media_type", 1)
            node: dict[str, Any] = {
                "shortcode": item.get("code", ""),
                "__typename": INSTAGRAM_MEDIA_TYPES.get(item_type, "GraphImage"),
                "is_video": item_type == 2,
            }
            item_candidates = (item.get("image_versions2") or {}).get("candidates") or []
            if item_candidates and isinstance(item_candidates[0], dict):
                node["display_url"] = item_candidates[0].get("url")
            item_videos = item.get("video_versions") or []
            if item_videos and isinstance(item_videos[0], dict):
                node["video_url"] = item_videos[0].get("url")
            carousel_nodes.append({"node": node})
        legacy["edge_sidecar_to_children"] = {"edges": carousel_nodes}

    tagged = (media.get("usertags") or {}).get("in") or []
    if tagged:
        legacy["edge_media_to_tagged_user"] = {
            "edges": [
                {"node": {"user": {"username": str(t["user"]["username"]).lower()}}}
                for t in tagged
                if isinstance(t, dict) and isinstance(t.get("user"), dict) and t["user"].get("username")
            ]
        }

    return legacy


def _format_instagram_graphql_errors(payload: dict[str, Any]) -> str:
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return "Instagram GraphQL returned no post data"
    messages: list[str] = []
    for item in errors[:3]:
        if isinstance(item, dict):
            message = str(item.get("message") or item.get("description") or item).strip()
            if message:
                messages.append(message)
        elif item:
            messages.append(str(item))
    return "; ".join(messages) if messages else "Instagram GraphQL returned no post data"


async def _scrape_post_once(shortcode: str) -> dict[str, Any]:
    log.info("scraping instagram post: %s", shortcode)
    variables = _instagram_post_graphql_variables(shortcode)
    query_url = (
        "https://www.instagram.com/graphql/query?"
        + urlencode(
            {
                "variables": variables,
                "doc_id": INSTAGRAM_DOCUMENT_ID,
                "server_timestamps": "true",
            }
        )
    )
    client = get_scrapfly_client()
    result = await client.async_scrape(
        ScrapeConfig(
            url=query_url,
            method="GET",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "x-ig-app-id": INSTAGRAM_APP_ID,
            },
            **BASE_CONFIG,
        )
    )
    maybe_record_scrapfly(result, operation="instagram_post", metadata={"shortcode": shortcode})
    payload = parse_scrapfly_json(result, operation=f"instagram post {shortcode}")
    media = _extract_post_media_from_graphql(payload, shortcode=shortcode)
    return parse_post(media)


async def scrape_user_posts(username: str, page_size: int = 12, max_pages: int | None = None):
    base_url = "https://www.instagram.com/graphql/query/"
    variables: dict[str, Any] = {
        "after": None,
        "before": None,
        "data": {
            "count": page_size,
            "include_reel_media_seen_timestamp": True,
            "include_relationship_info": True,
            "latest_besties_reel_media": True,
            "latest_reel_media": True,
        },
        "first": page_size,
        "last": None,
        "username": username,
        "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        "__relay_internal__pv__PolarisShareSheetV3relayprovider": True,
    }

    prev_cursor = None
    page_number = 1
    client = get_scrapfly_client()

    while True:
        params = {
            "doc_id": INSTAGRAM_ACCOUNT_DOCUMENT_ID,
            "variables": json.dumps(variables, separators=(",", ":")),
        }
        final_url = f"{base_url}?{urlencode(params)}"
        discovery_log(
            f"Instagram @{username}: {page_number}. oldal lekérése (Scrapfly)…",
            metadata={"platform": "instagram", "username": username, "page": page_number},
        )
        result = await client.async_scrape(
            ScrapeConfig(
                final_url,
                **BASE_CONFIG,
                method="GET",
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
        )
        maybe_record_scrapfly(
            result,
            operation="instagram_user_posts",
            metadata={"username": username, "page": page_number},
        )
        data = parse_scrapfly_json(result, operation=f"instagram timeline @{username} p{page_number}")
        posts = data["data"]["xdt_api__v1__feed__user_timeline_graphql_connection"]
        page_posts = len(posts["edges"])
        page_info = posts["page_info"]
        discovery_log(
            f"Instagram @{username}: {page_number}. oldal — HTTP {result.status_code}, "
            f"{page_posts} poszt"
            + (", lapozás…" if page_info["has_next_page"] else ", utolsó oldal"),
            metadata={
                "platform": "instagram",
                "username": username,
                "page": page_number,
                "posts_on_page": page_posts,
                "status_code": result.status_code,
                "has_next_page": page_info["has_next_page"],
            },
        )
        for post in posts["edges"]:
            yield parse_user_posts(post["node"])

        if not page_info["has_next_page"]:
            break

        if page_info["end_cursor"] == prev_cursor:
            log.warning("found no new instagram posts, breaking")
            discovery_log(f"Instagram @{username}: nincs új oldal (cursor ismétlődés), leállás")
            break

        prev_cursor = page_info["end_cursor"]
        variables["after"] = page_info["end_cursor"]
        page_number += 1

        if max_pages and page_number > max_pages:
            break


async def discover_instagram_posts(
    username: str,
    *,
    forward_since: str | None = None,
    backward_before: str | None = None,
    known_urls: set[str] | None = None,
    limit: int | None = None,
    max_pages: int = 50,
    on_post: Callable[[dict[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    """Discover Instagram posts: newer than forward_since first, then older posts."""
    forward_label = forward_since[:10] if forward_since else "nincs"
    backward_label = backward_before[:10] if backward_before else "nincs"
    limit_label = str(limit) if limit and limit > 0 else "korlátlan"
    discovery_log(
        f"Instagram @{username}: keresés (újabb: {forward_label}, régebbi: {backward_label}, max {limit_label})",
        metadata={
            "platform": "instagram",
            "username": username,
            "forward_since": forward_since,
            "backward_before": backward_before,
            "limit": limit,
        },
    )
    collected: list[dict[str, Any]] = []
    phase = "forward"
    logged_backward = False

    async for post in scrape_user_posts(username, max_pages=max_pages):
        shortcode = post.get("shortcode")
        if not shortcode:
            continue
        post_url = normalize_url(instagram_post_url(str(shortcode)))
        published = parse_unix_timestamp(post.get("taken_at"))
        is_known = bool(known_urls and post_url in known_urls)
        previous_phase = phase
        phase, should_collect = instagram_discovery_step(
            phase=phase,
            forward_since=forward_since,
            published=published,
            is_known=is_known,
        )
        if (
            not logged_backward
            and previous_phase == "forward"
            and phase == "backward"
            and forward_since
        ):
            discovery_log(
                f"Instagram @{username}: nincs újabb poszt — régebbiek keresése ({backward_label} alatt)…",
                metadata={"platform": "instagram", "username": username, "phase": "backward"},
            )
            logged_backward = True
        if not should_collect:
            continue
        if on_post is not None:
            if not on_post(post):
                break
        else:
            collected.append(post)
            if limit and limit > 0 and len(collected) >= limit:
                break

    phase_note = "újabb + régebbi" if phase == "backward" and forward_since else ("újabb" if forward_since else "teljes")
    if on_post is None:
        discovery_log(
            f"Instagram @{username}: {len(collected)} jelölt forrás ({phase_note})",
            metadata={"platform": "instagram", "username": username, "collected": len(collected), "phase": phase},
        )
    else:
        discovery_log(
            f"Instagram @{username}: lapozás kész ({phase_note})",
            metadata={"platform": "instagram", "username": username, "phase": phase},
        )
    return collected


async def collect_user_posts_since(
    username: str,
    *,
    since_iso: str | None = None,
    max_pages: int = 50,
    known_urls: set[str] | None = None,
) -> list[dict[str, Any]]:
    return await discover_instagram_posts(
        username,
        forward_since=since_iso,
        known_urls=known_urls,
        max_pages=max_pages,
    )


async def collect_user_posts(username: str, max_posts: int = 50) -> list[dict[str, Any]]:
    max_pages = max(1, (max_posts + 11) // 12)
    return await collect_user_posts_since(username, since_iso=None, max_pages=max_pages)


def instagram_post_url(shortcode: str) -> str:
    return f"https://www.instagram.com/p/{shortcode}/"


def instagram_discovery_step(
    *,
    phase: str,
    forward_since: str | None,
    published: str | None,
    is_known: bool,
) -> tuple[str, bool]:
    """Pure helper: returns (next_phase, should_collect)."""
    if is_known:
        return phase, False
    if phase == "forward":
        if forward_since and published and not is_newer_than(published, forward_since):
            return "backward", True
        return "forward", True
    if forward_since and published and is_newer_than(published, forward_since):
        return "backward", False
    return "backward", True


def _caption_text(caption: Any) -> str:
    if caption is None:
        return ""
    if isinstance(caption, str):
        return caption
    if isinstance(caption, dict):
        return str(caption.get("text") or caption.get("caption") or "")
    return str(caption)


def extract_instagram_caption(post: dict[str, Any]) -> str:
    caption = _caption_text(post.get("caption")).strip()
    if caption:
        return caption
    captions = post.get("captions")
    if isinstance(captions, list) and captions:
        return str(captions[0]).strip()
    return ""


def format_instagram_post_text(post: dict[str, Any], username: str | None = None) -> str:
    lines: list[str] = []
    if username:
        lines.append(f"@{username}")
    caption = extract_instagram_caption(post)
    if caption:
        lines.append(caption)
    if post.get("title"):
        lines.append(str(post["title"]))
    metrics = []
    for key, label in (("like_count", "likes"), ("comment_count", "comments"), ("likes", "likes")):
        value = post.get(key)
        if value is not None:
            metrics.append(f"{label}: {value}")
    if metrics:
        lines.append("")
        lines.append(" | ".join(metrics))
    comments = post.get("comments") or []
    if comments:
        lines.append("")
        lines.append("Comments:")
        for comment in comments[:5]:
            if isinstance(comment, dict):
                owner = comment.get("owner") or comment.get("owner_username") or "user"
                text = comment.get("text") or ""
                lines.append(f"- @{owner}: {text}")
    return "\n".join(lines).strip()
