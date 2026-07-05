"""Social post enrichment: Supadata video transcripts and carousel image OCR."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from memory_builder.env import load_project_env
from memory_builder.fetch.downloader import fetch_url, save_raw_bytes
from memory_builder.fetch.supadata_client import fetch_transcript, normalize_supadata_url
from memory_builder.models import MediaFormat, SourceNature


log = logging.getLogger(__name__)

VISION_MODEL = "gpt-4o"
VISION_PROMPT = (
    "Extract all text from this image. Only return the text content, no explanations. "
    "If there's no text, return 'No text found in image.'"
)
NO_TEXT_MARKER = "No text found in image."


def append_transcript_section(text: str, transcript: str) -> str:
    cleaned = transcript.strip()
    if not cleaned:
        return text
    base = text.rstrip()
    return f"{base}\n\n## Transcript\n\n{cleaned}"


def append_image_texts_section(text: str, image_texts: list[str]) -> str:
    usable = [item.strip() for item in image_texts if item.strip() and item.strip() != NO_TEXT_MARKER]
    if not usable:
        return text
    lines = [text.rstrip(), "", "## Képek szövege", ""]
    for index, item in enumerate(usable, start=1):
        lines.append(f"### {index}. kép")
        lines.append("")
        lines.append(item)
        lines.append("")
    return "\n".join(lines).strip()


def instagram_has_video(post: dict[str, Any]) -> bool:
    if post.get("is_video"):
        return True
    for item in post.get("images") or []:
        if isinstance(item, dict) and item.get("is_video"):
            return True
    return False


def instagram_image_urls(post: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    images = post.get("images")
    if isinstance(images, list) and images:
        for item in images:
            if not isinstance(item, dict):
                continue
            if item.get("is_video"):
                continue
            url = item.get("display_url") or item.get("src")
            if url:
                urls.append(str(url))
        return urls
    if post.get("is_video"):
        return []
    src = post.get("src")
    if src:
        urls.append(str(src))
    return urls


def instagram_cover_image_urls(post: dict[str, Any]) -> list[str]:
    """Cover/thumbnail frames for video posts — used for OCR when audio is unavailable."""
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: object) -> None:
        if not url:
            return
        value = str(url)
        if value not in seen:
            seen.add(value)
            urls.append(value)

    if post.get("is_video"):
        add(post.get("src"))
    for item in post.get("images") or []:
        if not isinstance(item, dict):
            continue
        if item.get("is_video"):
            add(item.get("display_url") or item.get("src"))
    return urls


def tweet_has_video(tweet: dict[str, Any], source_url: str) -> bool:
    for item in tweet.get("media") or []:
        if isinstance(item, dict) and str(item.get("type") or "").lower() == "video":
            return True
    lowered = source_url.lower()
    return "/status/" in lowered and "/video/" in lowered


def tweet_image_urls(tweet: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in tweet.get("media") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() != "photo":
            continue
        url = item.get("url")
        if url:
            urls.append(str(url))
    attached = tweet.get("attached_media") or []
    if not urls and isinstance(attached, list):
        for url in attached:
            if url and "amplify_video" not in str(url):
                urls.append(str(url))
    return urls


def facebook_has_video(source_url: str) -> bool:
    lowered = source_url.lower()
    return any(token in lowered for token in ("/reel/", "/reels/", "/videos/", "/watch/"))


def is_social_video_reprocess_url(source_url: str) -> bool:
    lowered = source_url.lower()
    if any(token in lowered for token in ("/reel/", "/reels/", "/video/", "/videos/", "/watch/")):
        return True
    if "instagram.com" in lowered and "/p/" not in lowered:
        return "/reel/" in lowered
    return False


def should_reprocess_social_transcript(
    persona_id: str,
    source_url: str,
    root: Path | None = None,
    *,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """True when a social source should use the spoken transcript reprocess path."""
    from memory_builder.fetch.downloader import source_slug
    from memory_builder.paths import project_root, sources_processed_dir, sources_raw_dir

    meta = metadata if metadata is not None else {}
    if meta.get("transcription_provider") == "supadata":
        return True
    if meta.get("attribution_mode") in {"audio_diarized", "text_attributed"}:
        return True
    if meta.get("transcription_mode") in {"diarized", "text_attributed"}:
        return True
    if is_social_video_reprocess_url(source_url):
        return True

    base_root = root or project_root()
    slug = source_slug(source_url)
    processed_dir = sources_processed_dir(persona_id, base_root) / slug
    if (processed_dir / "transcript_segments.json").exists() or (processed_dir / "raw_transcript.txt").exists():
        return True

    raw_social = sources_raw_dir(persona_id, base_root) / slug / "social.json"
    if raw_social.exists():
        try:
            payload = json.loads(raw_social.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        post = payload.get("post") if isinstance(payload, dict) else None
        if isinstance(post, dict):
            if post.get("is_video"):
                return True
            if instagram_has_video(post):
                return True
            if tweet_has_video(post, source_url):
                return True
        if facebook_has_video(source_url):
            return True
    return False


def resolve_source_nature(*, has_transcript: bool, base_text: str) -> str:
    if has_transcript:
        return SourceNature.NATURAL_SPOKEN
    if base_text.strip():
        return SourceNature.WRITTEN
    return SourceNature.UNCERTAIN


def classify_social_media_format(*, has_video: bool, has_images: bool, has_text: bool) -> str:
    """Primary media modality of a social post. Priority: video > image > text."""
    if has_video:
        return MediaFormat.VIDEO
    if has_images:
        return MediaFormat.IMAGE
    if has_text:
        return MediaFormat.TEXT
    return MediaFormat.UNKNOWN


def instagram_media_format(post: dict[str, Any]) -> str:
    has_text = bool(post.get("caption") or post.get("captions"))
    return classify_social_media_format(
        has_video=instagram_has_video(post),
        has_images=bool(instagram_image_urls(post)),
        has_text=has_text,
    )


def tweet_media_format(tweet: dict[str, Any], source_url: str) -> str:
    has_text = bool(str(tweet.get("full_text") or tweet.get("text") or "").strip())
    return classify_social_media_format(
        has_video=tweet_has_video(tweet, source_url),
        has_images=bool(tweet_image_urls(tweet)),
        has_text=has_text,
    )


def maybe_fetch_video_transcript(source_url: str, *, has_video: bool) -> tuple[str | None, dict[str, Any]]:
    if not has_video:
        return None, {}
    try:
        transcript = fetch_transcript(source_url)
        return transcript, {
            "transcription_provider": "supadata",
            "transcription_url": normalize_supadata_url(source_url),
        }
    except Exception as exc:
        message = str(exc)
        if "no audio track" in message.lower():
            log.info("Supadata skipped (no audio track) for %s", source_url)
        else:
            log.warning("Supadata transcript failed for %s: %s", source_url, exc)
        return None, {"transcription_error": message}


def _openai_api_key() -> str:
    load_project_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for social image OCR")
    return key


def extract_text_from_image(image_path: Path) -> str:
    api_key = _openai_api_key()
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        },
        timeout=90.0,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenAI vision returned no choices for {image_path.name}")
    message = choices[0].get("message") or {}
    text = str(message.get("content") or "").strip()
    _record_openai_vision_usage(payload, image_path=image_path.name)
    return text or NO_TEXT_MARKER


def _record_openai_vision_usage(payload: dict[str, Any], *, image_path: str) -> None:
    from memory_builder.telemetry.context import get_run_context
    from memory_builder.telemetry.pricing import estimate_openai_vision_cost_usd

    usage = payload.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    ctx = get_run_context()
    if not ctx:
        return
    ctx.record_api_usage(
        provider="openai",
        operation="vision_ocr",
        model=VISION_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_openai_vision_cost_usd(
            model=VISION_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        is_estimated=input_tokens == 0 and output_tokens == 0,
        metadata={"image_file": image_path},
    )


def _image_suffix(url: str, content: bytes, index: int) -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(ext):
            return f"images/image_{index}{ext if ext != '.jpeg' else '.jpg'}"
    if content[:3] == b"\xff\xd8\xff":
        return f"images/image_{index}.jpg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return f"images/image_{index}.png"
    return f"images/image_{index}.jpg"


def process_image_urls(
    image_urls: list[str],
    *,
    persona_id: str,
    source_url: str,
    root: Path,
) -> tuple[list[str], list[str]]:
    if not image_urls:
        return [], []
    saved_paths: list[str] = []
    texts: list[str] = []
    for index, image_url in enumerate(image_urls, start=1):
        try:
            content, _headers = fetch_url(image_url, timeout=60.0)
            suffix = _image_suffix(image_url, content, index)
            image_path = save_raw_bytes(persona_id, source_url, suffix, content, root)
            saved_paths.append(str(image_path))
            texts.append(extract_text_from_image(image_path))
        except Exception as exc:
            log.warning("Image OCR failed for %s: %s", image_url, exc)
            texts.append(f"[Error processing image: {exc}]")
    return texts, saved_paths
