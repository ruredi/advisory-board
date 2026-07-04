from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_facebook import format_facebook_post_text, is_facebook_post_url, scrape_facebook_post
from memory_builder.fetch.scrapfly_instagram import format_instagram_post_text, scrape_post
from memory_builder.fetch.scrapfly_twitter import format_tweet_text, scrape_tweet
from memory_builder.fetch.downloader import save_json_metadata, source_slug
from memory_builder.models import ProcessedDocument
from memory_builder.paths import project_root, sources_processed_dir
from memory_builder.processors.social_media_enrichment import (
    append_image_texts_section,
    append_transcript_section,
    facebook_has_video,
    instagram_has_video,
    instagram_image_urls,
    maybe_fetch_video_transcript,
    process_image_urls,
    resolve_source_nature,
    tweet_has_video,
    tweet_image_urls,
)


def social_platform(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    if any(token in host for token in ("x.com", "twitter.com")):
        return "x"
    if "instagram.com" in host:
        return "instagram"
    if is_facebook_post_url(url):
        return "facebook"
    return None


def _enrich_social_text(
    *,
    persona_id: str,
    source_url: str,
    base_text: str,
    root: Path,
    has_video: bool,
    image_urls: list[str],
    metadata: dict,
) -> tuple[str, str, dict]:
    text = base_text
    enrichment: dict = {}

    transcript, transcript_meta = maybe_fetch_video_transcript(source_url, has_video=has_video)
    if transcript:
        text = append_transcript_section(text, transcript)
        enrichment.update(transcript_meta)
        enrichment["transcript"] = transcript
        enrichment["transcript_chars"] = len(transcript)

    if image_urls:
        image_texts, saved_paths = process_image_urls(
            image_urls,
            persona_id=persona_id,
            source_url=source_url,
            root=root,
        )
        if image_texts:
            text = append_image_texts_section(text, image_texts)
            enrichment["image_ocr_count"] = len(image_texts)
            enrichment["image_paths"] = saved_paths

    source_nature = resolve_source_nature(has_transcript=bool(transcript), base_text=base_text)
    metadata.update(enrichment)
    return text, source_nature, metadata


def process_social_post(persona_id: str, source_url: str, root: Path | None = None) -> ProcessedDocument:
    base_root = root or project_root()
    platform = social_platform(source_url)
    if platform == "x":
        tweet = run_async(scrape_tweet(source_url))
        text = format_tweet_text(tweet)
        user = tweet.get("user") or {}
        title = f"@{user.get('screen_name', 'x')} — {tweet.get('id', source_url)}"
        metadata = {"source_url": source_url, "platform": "x", "tweet": tweet}
        has_video = tweet_has_video(tweet, source_url)
        image_urls = tweet_image_urls(tweet) if not has_video else []
        text, source_nature, metadata = _enrich_social_text(
            persona_id=persona_id,
            source_url=source_url,
            base_text=text,
            root=base_root,
            has_video=has_video,
            image_urls=image_urls,
            metadata=metadata,
        )
    elif platform == "instagram":
        post = run_async(scrape_post(source_url))
        username = _instagram_username_from_url(source_url)
        text = format_instagram_post_text(post, username=username)
        shortcode = post.get("shortcode") or source_url
        title = f"Instagram — {shortcode}"
        metadata = {"source_url": source_url, "platform": "instagram", "post": post}
        has_video = instagram_has_video(post)
        image_urls = instagram_image_urls(post)
        text, source_nature, metadata = _enrich_social_text(
            persona_id=persona_id,
            source_url=source_url,
            base_text=text,
            root=base_root,
            has_video=has_video,
            image_urls=image_urls,
            metadata=metadata,
        )
    elif platform == "facebook":
        post = run_async(scrape_facebook_post(source_url))
        text = format_facebook_post_text(post)
        post_id = post.get("post_id") or source_url
        title = f"Facebook — {post_id}"
        metadata = {"source_url": source_url, "platform": "facebook", "post": post}
        has_video = facebook_has_video(source_url)
        text, source_nature, metadata = _enrich_social_text(
            persona_id=persona_id,
            source_url=source_url,
            base_text=text,
            root=base_root,
            has_video=has_video,
            image_urls=[],
            metadata=metadata,
        )
    else:
        raise RuntimeError(f"Unsupported social URL: {source_url}")

    if not text.strip():
        raise RuntimeError(f"No text extracted from social post: {source_url}")

    transcript_only = metadata.pop("transcript", None)

    raw_dir = base_root / "sources" / "raw" / persona_id / source_slug(source_url)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "social.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    save_json_metadata(persona_id, source_url, metadata, base_root)

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "document.txt").write_text(text, encoding="utf-8")
    if isinstance(transcript_only, str) and transcript_only.strip():
        (processed_dir / "transcript.txt").write_text(transcript_only.strip(), encoding="utf-8")

    return ProcessedDocument(
        title=title,
        text=text,
        source_nature=source_nature,
        metadata=metadata,
    )


def _instagram_username_from_url(source_url: str) -> str | None:
    path = urlparse(source_url).path.strip("/")
    if not path:
        return None
    first = path.split("/")[0]
    if first in {"p", "reel", "stories", "explore"}:
        return None
    return first
