"""Facebook page/profile/group scraping via Scrapfly.

Supports public personal pages, business pages, and groups. Group discovery keeps
only posts published by the group (Group/Page actor), not member posts.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from scrapfly import ScrapeConfig

from memory_builder.fetch.scrapfly_client import get_scrapfly_client
from memory_builder.telemetry.usage_helpers import maybe_record_scrapfly


log = logging.getLogger(__name__)

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
    "proxy_pool": "public_residential_pool",
}
RENDER_WAIT_MS = 10_000
JSON_SCRIPT_PATTERN = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.DOTALL)
OG_DESCRIPTION_PATTERN = re.compile(r'<meta property="og:description" content="([^"]*)"', re.IGNORECASE)
OG_TITLE_PATTERN = re.compile(r'<meta property="og:title" content="([^"]*)"', re.IGNORECASE)
POST_LINK_PATTERN = re.compile(
    r'href="(?:https?:\\/\\/(?:www\\.|m\\.)?facebook\\.com)?([^"?]*/(?:posts|reel)/[^"?]+)"',
    re.IGNORECASE,
)
RESERVED_FACEBOOK_PATHS = frozenset(
    {
        "watch",
        "share",
        "sharer",
        "login",
        "recover",
        "help",
        "policies",
        "events",
        "marketplace",
        "gaming",
        "reels",
        "videos",
        "people",
        "search",
    }
)
GROUP_OFFICIAL_ACTOR_TYPES = frozenset({"Group", "Page"})


@dataclass(frozen=True)
class FacebookTarget:
    kind: str  # profile | page | group | post
    slug: str
    url: str


def _optional_close_modal_scenario(scroll_count: int = 4) -> list[dict[str, Any]]:
    scenario: list[dict[str, Any]] = [
        {
            "wait_for_selector": {
                "selector": "div[aria-label='Close']",
                "timeout": 2000,
                "ignore": True,
            }
        },
        {"click": {"selector": "div[aria-label='Close']", "ignore": True}},
        {"wait": 500},
    ]
    for _ in range(scroll_count):
        scenario.append({"scroll": {"selector": "bottom"}})
        scenario.append({"wait": 1200})
    return scenario


def parse_facebook_target(url: str) -> FacebookTarget | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    if host not in {"facebook.com", "fb.com"}:
        return None

    path = parsed.path.strip("/")
    if not path:
        return None

    parts = [part for part in path.split("/") if part]
    lowered = [part.lower() for part in parts]

    if lowered[0] == "groups":
        if len(parts) >= 3 and lowered[2] == "posts":
            return FacebookTarget(kind="post", slug="/".join(parts), url=url)
        if len(parts) >= 2:
            return FacebookTarget(
                kind="group",
                slug=parts[1],
                url=f"https://www.facebook.com/groups/{parts[1]}/",
            )
        return None

    if lowered[0] in {"reel", "reels"} and len(parts) >= 2:
        return FacebookTarget(kind="post", slug=parts[1], url=url)

    if lowered[0] == "permalink.php" or path.endswith("permalink.php"):
        return FacebookTarget(kind="post", slug=parsed.query or path, url=url)

    if lowered[0] in RESERVED_FACEBOOK_PATHS:
        return None

    if is_facebook_post_url(url):
        return FacebookTarget(kind="post", slug=path, url=url)

    if len(parts) == 1:
        return FacebookTarget(
            kind="page",
            slug=parts[0],
            url=f"https://www.facebook.com/{parts[0]}/",
        )

    if lowered[0] == "pages" and len(parts) >= 2:
        return FacebookTarget(
            kind="page",
            slug=parts[1],
            url=f"https://www.facebook.com/{parts[1]}/",
        )

    if lowered[1] == "posts" and len(parts) >= 3:
        return FacebookTarget(kind="post", slug="/".join(parts), url=url)

    return None


def _canonical_profile_url(url: str) -> str:
    target = parse_facebook_target(url)
    if target is None or target.kind == "post":
        return url
    return target.url


def is_facebook_profile_url(url: str) -> bool:
    target = parse_facebook_target(url)
    return target is not None and target.kind in {"page", "group", "profile"}


def is_facebook_post_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "facebook.com" not in host and "fb.com" not in host:
        return False
    path = parsed.path.lower()
    if "/posts/" in path or "/reel/" in path or path.startswith("/reel/"):
        return True
    if path.endswith("permalink.php") or "story_fbid" in url.lower():
        return True
    if "/groups/" in path and "/posts/" in path:
        return True
    if path.startswith("/photo.php") and "fbid=" in url.lower():
        return True
    return False


async def _scrape_facebook_page(url: str, *, scroll_count: int = 4) -> str:
    client = get_scrapfly_client()
    result = await client.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
            rendering_wait=RENDER_WAIT_MS,
            js_scenario=_optional_close_modal_scenario(scroll_count=scroll_count),
        )
    )
    maybe_record_scrapfly(result, operation="facebook_scrape", metadata={"url": url})
    return result.content or ""


def _decode_json_text(value: str) -> str:
    return html_lib.unescape(value.replace("\\n", "\n").replace("\\/", "/")).strip()


def _actor_info(actor: dict[str, Any]) -> dict[str, str]:
    return {
        "id": str(actor.get("id") or ""),
        "name": str(actor.get("name") or ""),
        "typename": str(actor.get("__typename") or ""),
        "url": str(actor.get("url") or actor.get("profile_url") or "").replace("\\/", "/"),
    }


def _message_text(message: Any) -> str:
    if isinstance(message, dict):
        return _decode_json_text(str(message.get("text") or ""))
    if isinstance(message, str):
        return _decode_json_text(message)
    return ""


def _walk_story_nodes(obj: Any, store: dict[str, dict[str, Any]], depth: int = 0) -> None:
    if depth > 40:
        return
    if isinstance(obj, dict):
        post_id = obj.get("post_id") or obj.get("legacy_story_id")
        message = _message_text(obj.get("message"))
        www_url = str(obj.get("wwwURL") or obj.get("url") or "").replace("\\/", "/")
        actors = [_actor_info(actor) for actor in (obj.get("actors") or []) if isinstance(actor, dict)]
        if post_id and (message or www_url or actors):
            key = str(post_id)
            existing = store.get(key, {})
            store[key] = {
                "post_id": key,
                "text": message or existing.get("text", ""),
                "wwwURL": www_url or existing.get("wwwURL", ""),
                "actors": actors or existing.get("actors", []),
                "typename": obj.get("__typename") or existing.get("typename"),
            }
        for value in obj.values():
            _walk_story_nodes(value, store, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _walk_story_nodes(item, store, depth + 1)


def extract_stories_from_html(page_html: str) -> list[dict[str, Any]]:
    store: dict[str, dict[str, Any]] = {}
    for script in JSON_SCRIPT_PATTERN.findall(page_html):
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        _walk_story_nodes(payload, store)
    return list(store.values())


def extract_post_links_from_html(page_html: str, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in POST_LINK_PATTERN.findall(page_html):
        path = match.replace("\\/", "/").lstrip("/")
        if not path:
            continue
        url = f"https://www.facebook.com/{path}"
        if url not in seen:
            seen.add(url)
            links.append(url)
    for story in extract_stories_from_html(page_html):
        www_url = story.get("wwwURL") or ""
        if www_url and www_url not in seen:
            seen.add(www_url)
            links.append(www_url)
    return links


def _matches_page_actor(story: dict[str, Any], slug: str) -> bool:
    slug_lower = slug.lower()
    for actor in story.get("actors") or []:
        name = str(actor.get("name") or "").lower()
        url = str(actor.get("url") or "").lower()
        if slug_lower in url or slug_lower == name.replace(" ", ""):
            return True
        if name and slug_lower.rstrip("s") in name.replace(" ", "").lower():
            return True
    return True


def is_group_official_post(story: dict[str, Any], group_slug: str) -> bool:
    actors = story.get("actors") or []
    if not actors:
        return False
    group_slug_lower = group_slug.lower()
    for actor in actors:
        typename = str(actor.get("typename") or "")
        name = str(actor.get("name") or "").lower()
        actor_id = str(actor.get("id") or "")
        url = str(actor.get("url") or "").lower()
        if typename in GROUP_OFFICIAL_ACTOR_TYPES:
            return True
        if group_slug_lower in url:
            return True
        if name and group_slug_lower.replace("-", " ") in name:
            return True
        if actor_id and group_slug_lower.isdigit() and actor_id == group_slug_lower:
            return True
    return False


def facebook_post_public_url(story: dict[str, Any], profile_url: str | None = None) -> str:
    www_url = str(story.get("wwwURL") or "").strip()
    if www_url:
        return www_url
    post_id = str(story.get("post_id") or "")
    actors = story.get("actors") or []
    if actors:
        actor_url = str(actors[0].get("url") or "")
        if actor_url and post_id:
            parsed = urlparse(actor_url)
            slug = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
            if slug:
                return f"https://www.facebook.com/{slug}/posts/{post_id}/"
    if profile_url and post_id:
        target = parse_facebook_target(profile_url)
        if target and target.kind == "group":
            return f"https://www.facebook.com/groups/{target.slug}/posts/{post_id}/"
        if target and target.slug:
            return f"https://www.facebook.com/{target.slug}/posts/{post_id}/"
    return profile_url or f"https://www.facebook.com/posts/{post_id}"


def _parse_post_from_html(url: str, page_html: str) -> dict[str, Any]:
    og_description = OG_DESCRIPTION_PATTERN.search(page_html)
    og_title = OG_TITLE_PATTERN.search(page_html)
    text = _decode_json_text(og_description.group(1)) if og_description else ""
    title = _decode_json_text(og_title.group(1)) if og_title else ""
    stories = extract_stories_from_html(page_html)
    story = stories[0] if stories else {}
    if not text:
        text = str(story.get("text") or "")
    post_id = str(story.get("post_id") or "")
    if not post_id:
        path = urlparse(url).path
        reel_match = re.search(r"/reel/(\d+)", path)
        if reel_match:
            post_id = reel_match.group(1)
        else:
            post_match = re.search(r"/posts/([^/]+)", path)
            if post_match:
                post_id = post_match.group(1)
    return {
        "post_id": post_id,
        "text": text,
        "title": title,
        "url": url,
        "actors": story.get("actors") or [],
        "wwwURL": url,
    }


async def scrape_facebook_post(url: str) -> dict[str, Any]:
    log.info("scraping facebook post %s", url)
    page_html = await _scrape_facebook_page(url, scroll_count=1)
    post = _parse_post_from_html(url, page_html)
    if not post.get("text"):
        raise RuntimeError(f"No text extracted from Facebook post: {url}")
    return post


async def scrape_facebook_timeline(profile_url: str, *, max_posts: int = 50) -> list[dict[str, Any]]:
    target = parse_facebook_target(profile_url)
    if target is None or target.kind == "post":
        raise ValueError(f"Not a Facebook profile/page/group URL: {profile_url}")

    canonical_url = _canonical_profile_url(profile_url)
    page_html = await _scrape_facebook_page(canonical_url, scroll_count=6)
    stories = extract_stories_from_html(page_html)
    links = extract_post_links_from_html(page_html, canonical_url)

    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    def add_story(story: dict[str, Any]) -> None:
        if target.kind == "group" and not is_group_official_post(story, target.slug):
            return
        if target.kind in {"page", "profile"} and not _matches_page_actor(story, target.slug):
            return
        post_url = facebook_post_public_url(story, canonical_url)
        if post_url in seen_urls:
            return
        seen_urls.add(post_url)
        story = dict(story)
        story["wwwURL"] = post_url
        collected.append(story)

    for story in stories:
        add_story(story)
        if len(collected) >= max_posts:
            break

    for link in links:
        if len(collected) >= max_posts:
            break
        if link in seen_urls:
            continue
        if target.kind == "group":
            continue
        seen_urls.add(link)
        collected.append({"post_id": "", "text": "", "wwwURL": link, "actors": []})

    if not collected:
        log.warning("Facebook timeline returned no posts for %s", canonical_url)
    return collected[:max_posts]


async def collect_facebook_posts(profile_url: str, max_posts: int = 50) -> list[dict[str, Any]]:
    return await scrape_facebook_timeline(profile_url, max_posts=max_posts)


def format_facebook_post_text(post: dict[str, Any]) -> str:
    lines: list[str] = []
    actors = post.get("actors") or []
    if actors:
        actor = actors[0]
        name = actor.get("name") or "facebook"
        lines.append(str(name))
    text = str(post.get("text") or "").strip()
    if text:
        lines.append(text)
    title = str(post.get("title") or "").strip()
    if title and title not in text:
        lines.append(title)
    url = str(post.get("wwwURL") or post.get("url") or "").strip()
    if url:
        lines.append("")
        lines.append(url)
    return "\n".join(lines).strip()


def facebook_profile_kind(url: str) -> str:
    target = parse_facebook_target(url)
    if target is None:
        return "page"
    return target.kind
