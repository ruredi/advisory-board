from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from memory_builder.fetch.async_utils import run_async
from memory_builder.fetch.scrapfly_facebook import format_facebook_post_text, is_facebook_post_url, scrape_facebook_post
from memory_builder.fetch.scrapfly_instagram import extract_instagram_caption, format_instagram_post_text, scrape_post
from memory_builder.fetch.scrapfly_twitter import format_tweet_text, scrape_tweet
from memory_builder.fetch.downloader import save_json_metadata, source_slug
from memory_builder.models import MediaFormat, ProcessedDocument
from memory_builder.paths import project_root, sources_processed_dir
from memory_builder.processors.social_media_enrichment import (
    append_image_texts_section,
    classify_social_media_format,
    facebook_has_video,
    instagram_cover_image_urls,
    instagram_has_video,
    instagram_image_urls,
    maybe_fetch_video_transcript,
    process_image_urls,
    resolve_source_nature,
    tweet_has_video,
    tweet_image_urls,
)
from memory_builder.processors.speaker_turns import build_written_extraction_input
from memory_builder.processors.transcript_pipeline import build_text_attributed_document_text


HASHTAG_RE = re.compile(r"#\w+")
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
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


def process_social_post(
    persona_id: str,
    source_url: str,
    root: Path | None = None,
    *,
    transcription_model: str = "gemini-2.5-flash",
    source_title: str = "",
    display_name: str = "",
    speaker_names: list[str] | None = None,
    speaker_labeled_transcription: bool = False,
    channel_url: str = "",
) -> ProcessedDocument:
    base_root = root or project_root()
    platform = social_platform(source_url)
    channel_url = channel_url.strip()
    if platform == "x":
        tweet = run_async(scrape_tweet(source_url))
        text = format_tweet_text(tweet)
        user = tweet.get("user") or {}
        screen_name = str(user.get("screen_name") or "x")
        title = source_title.strip() or f"@{screen_name} — {tweet.get('id', source_url)}"
        metadata = {
            "source_url": source_url,
            "platform": "x",
            "tweet": tweet,
            "channel_url": channel_url or f"https://x.com/{screen_name}",
        }
        has_video = tweet_has_video(tweet, source_url)
        image_urls = tweet_image_urls(tweet) if not has_video else []
        post_context = _x_post_context(tweet, screen_name)
    elif platform == "instagram":
        post = run_async(scrape_post(source_url))
        username = _instagram_username_from_url(source_url) or ""
        text = format_instagram_post_text(post, username=username or None)
        title = _instagram_display_title(
            post,
            username=username,
            source_title=source_title,
            channel_url=channel_url,
        )
        metadata = {
            "source_url": source_url,
            "platform": "instagram",
            "post": post,
            "channel_url": channel_url or (f"https://instagram.com/{username}" if username else ""),
        }
        has_video = instagram_has_video(post)
        image_urls = instagram_image_urls(post)
        post_context = _instagram_post_context(post, username)
    elif platform == "facebook":
        post = run_async(scrape_facebook_post(source_url))
        text = format_facebook_post_text(post)
        post_id = post.get("post_id") or source_url
        title = source_title.strip() or f"Facebook — {post_id}"
        metadata = {
            "source_url": source_url,
            "platform": "facebook",
            "post": post,
            "channel_url": channel_url,
        }
        has_video = facebook_has_video(source_url)
        image_urls: list[str] = []
        post_context = text.split("\n\n")[0].strip() if text.strip() else ""
    else:
        raise RuntimeError(f"Unsupported social URL: {source_url}")

    media_format = classify_social_media_format(
        has_video=has_video,
        has_images=bool(image_urls),
        has_text=bool(text.strip() or post_context.strip()),
    )
    metadata["media_format"] = media_format

    enrichment: dict = {}
    ocr_context = ""
    if image_urls:
        image_texts, saved_paths = process_image_urls(
            image_urls,
            persona_id=persona_id,
            source_url=source_url,
            root=base_root,
        )
        if image_texts:
            ocr_context = "\n\n".join(item.strip() for item in image_texts if item.strip())
            enrichment["image_ocr_count"] = len(image_texts)
            enrichment["image_paths"] = saved_paths

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)

    transcript_text: str | None = None
    segments = None
    artifact_paths: dict[str, str] = {}
    if has_video:
        transcript_text, transcript_meta = maybe_fetch_video_transcript(source_url, has_video=True)
        enrichment.update(transcript_meta)
        if not transcript_text:
            cover_urls = instagram_cover_image_urls(post) if platform == "instagram" else []
            if cover_urls:
                cover_texts, cover_paths = process_image_urls(
                    cover_urls,
                    persona_id=persona_id,
                    source_url=source_url,
                    root=base_root,
                )
                if cover_texts:
                    cover_ocr = "\n\n".join(item.strip() for item in cover_texts if item.strip())
                    if cover_ocr:
                        ocr_context = f"{ocr_context}\n\n{cover_ocr}".strip() if ocr_context else cover_ocr
                        enrichment["cover_ocr_count"] = len(cover_texts)
                        enrichment.setdefault("image_paths", []).extend(cover_paths)

    use_attribution = bool(has_video and transcript_text and display_name)
    if use_attribution:
        source_context = _source_context_block(title=title, channel_url=metadata.get("channel_url", ""))
        extraction_input, segments, artifact_paths = build_text_attributed_document_text(
            raw_transcript=transcript_text or "",
            transcription_model=transcription_model,
            display_name=display_name,
            speaker_names=speaker_names or [],
            processed_dir=processed_dir,
            post_context=post_context,
            source_context=source_context,
            ocr_context=ocr_context,
        )
        metadata.update(
            {
                "transcription_mode": "text_attributed",
                "attribution_mode": "text_attributed",
                "transcription_provider": enrichment.get("transcription_provider", "supadata"),
                "segment_count": len(segments.segments),
                "target_segment_count": sum(
                    1 for segment in segments.segments if segment.speaker_type == "target"
                ),
                **{f"path_{key}": value for key, value in artifact_paths.items()},
            }
        )
        document_text = extraction_input
        source_nature = resolve_source_nature(has_transcript=True, base_text=post_context)
        preview_text = post_context
        if ocr_context:
            preview_text = append_image_texts_section(preview_text, ocr_context.split("\n\n"))
    else:
        if has_video and not transcript_text:
            metadata["transcription_mode"] = "no_audio"
            metadata["attribution_mode"] = "none"
        caption_body = post_context.strip()
        document_text = build_written_extraction_input(
            "",
            post_context=caption_body,
            ocr_context=ocr_context,
        )
        preview_text = caption_body or extract_instagram_caption(post)
        if ocr_context:
            preview_text = append_image_texts_section(preview_text, ocr_context.split("\n\n"))
        source_nature = resolve_source_nature(
            has_transcript=False,
            base_text=caption_body or ocr_context,
        )
        (processed_dir / "extraction_input.txt").write_text(document_text, encoding="utf-8")
        (processed_dir / "transcript.txt").write_text(document_text, encoding="utf-8")
        if transcript_text:
            (processed_dir / "raw_transcript.txt").write_text(transcript_text.strip(), encoding="utf-8")

    if not document_text.strip():
        raise RuntimeError(f"No text extracted from social post: {source_url}")

    raw_dir = base_root / "sources" / "raw" / persona_id / source_slug(source_url)
    raw_dir.mkdir(parents=True, exist_ok=True)
    metadata.update(enrichment)
    metadata["source_title"] = title
    (raw_dir / "social.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    save_json_metadata(persona_id, source_url, metadata, base_root)

    (processed_dir / "document.txt").write_text(preview_text, encoding="utf-8")

    return ProcessedDocument(
        title=title,
        text=document_text,
        source_nature=source_nature,
        media_format=media_format,
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


def _sanitize_title_text(text: str, *, max_len: int = 120) -> str:
    cleaned = HASHTAG_RE.sub("", text)
    cleaned = EMOJI_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—|")
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1].rstrip() + "…"
    return cleaned


def _instagram_display_title(
    post: dict,
    *,
    username: str,
    source_title: str,
    channel_url: str,
) -> str:
    if source_title.strip():
        return source_title.strip()[:200]
    caption = extract_instagram_caption(post)
    first_line = caption.split("\n", maxsplit=1)[0].strip() if caption else ""
    sanitized = _sanitize_title_text(first_line)
    if len(sanitized) >= 20:
        return sanitized[:200]
    account = username or ""
    if not account and channel_url:
        account = channel_url.rstrip("/").split("/")[-1]
    taken_at = post.get("taken_at") or post.get("timestamp")
    date_label = ""
    if taken_at:
        try:
            ts = int(taken_at)
            date_label = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date_label = ""
    if account and date_label:
        return f"@{account} — {date_label}"
    if account:
        return f"@{account}"
    shortcode = post.get("shortcode") or "post"
    return f"Instagram — {shortcode}"


def _instagram_post_context(post: dict, username: str) -> str:
    lines: list[str] = []
    if username:
        lines.append(f"@{username}")
    caption = extract_instagram_caption(post)
    if caption:
        lines.append(caption)
    return "\n".join(lines).strip()


def _x_post_context(tweet: dict, screen_name: str) -> str:
    lines = [f"@{screen_name}"]
    body = str(tweet.get("full_text") or tweet.get("text") or "").strip()
    if body:
        lines.append(body)
    return "\n".join(lines).strip()


def _source_context_block(*, title: str, channel_url: str) -> str:
    lines = [f"Title: {title.strip()}"]
    if channel_url.strip():
        lines.append(f"Channel: {channel_url.strip()}")
    return "\n".join(lines)
