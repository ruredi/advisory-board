"""Instagram scraping via Scrapfly — adapted from secret-project/scrapfly-scrapers/instagram-scraper."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlencode

import jmespath
from scrapfly import ScrapeConfig

from memory_builder.fetch.scrapfly_client import get_scrapfly_client
from memory_builder.telemetry.usage_helpers import maybe_record_scrapfly


log = logging.getLogger(__name__)

BASE_CONFIG = {
    "asp": True,
    "country": "CA",
}
INSTAGRAM_APP_ID = "936619743392459"
INSTAGRAM_DOCUMENT_ID = "8845758582119845"
INSTAGRAM_ACCOUNT_DOCUMENT_ID = "9310670392322965"


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
    result.update(parse_comments(data))
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
    data = json.loads(result.content)
    return parse_user(data["data"]["user"])


async def scrape_post(url_or_shortcode: str) -> dict[str, Any]:
    if "http" in url_or_shortcode:
        shortcode = url_or_shortcode.split("/p/")[-1].split("/reel/")[-1].split("/")[0]
    else:
        shortcode = url_or_shortcode
    log.info("scraping instagram post: %s", shortcode)
    variables = json.dumps(
        {
            "shortcode": shortcode,
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        },
        separators=(",", ":"),
    )
    body = f"variables={variables}&doc_id={INSTAGRAM_DOCUMENT_ID}"
    client = get_scrapfly_client()
    result = await client.async_scrape(
        ScrapeConfig(
            url="https://www.instagram.com/graphql/query",
            method="POST",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            **BASE_CONFIG,
        )
    )
    maybe_record_scrapfly(result, operation="instagram_post", metadata={"shortcode": shortcode})
    data = json.loads(result.content)
    return parse_post(data["data"]["xdt_shortcode_media"])


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
        data = json.loads(result.content)
        posts = data["data"]["xdt_api__v1__feed__user_timeline_graphql_connection"]
        for post in posts["edges"]:
            yield parse_user_posts(post["node"])

        page_info = posts["page_info"]
        if not page_info["has_next_page"]:
            break

        if page_info["end_cursor"] == prev_cursor:
            log.warning("found no new instagram posts, breaking")
            break

        prev_cursor = page_info["end_cursor"]
        variables["after"] = page_info["end_cursor"]
        page_number += 1

        if max_pages and page_number > max_pages:
            break


async def collect_user_posts(username: str, max_posts: int = 50) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    max_pages = max(1, (max_posts + 11) // 12)
    async for post in scrape_user_posts(username, max_pages=max_pages):
        posts.append(post)
        if len(posts) >= max_posts:
            break
    return posts


def instagram_post_url(shortcode: str) -> str:
    return f"https://www.instagram.com/p/{shortcode}/"


def _caption_text(caption: Any) -> str:
    if caption is None:
        return ""
    if isinstance(caption, str):
        return caption
    if isinstance(caption, dict):
        return str(caption.get("text") or caption.get("caption") or "")
    return str(caption)


def format_instagram_post_text(post: dict[str, Any], username: str | None = None) -> str:
    lines: list[str] = []
    if username:
        lines.append(f"@{username}")
    caption = _caption_text(post.get("caption"))
    if not caption and post.get("captions"):
        captions = post["captions"]
        if isinstance(captions, list) and captions:
            caption = str(captions[0])
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
