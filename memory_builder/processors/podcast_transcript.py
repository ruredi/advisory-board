from __future__ import annotations

import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from memory_builder.fetch.downloader import save_json_metadata, save_raw_bytes, source_slug
from memory_builder.gemini_client import build_gemini_client
from memory_builder.models import ProcessedDocument, SourceNature
from memory_builder.telemetry.context import get_run_context
from memory_builder.paths import project_root, sources_processed_dir


AUDIO_EXTENSIONS = (".mp3", ".m4a", ".wav", ".aac", ".ogg")
PSEUDO_PODCAST_ENTRY_PREFIX = "podcast-entry:"
INLINE_AUDIO_MAX_BYTES = 18 * 1024 * 1024
TRANSCRIBE_PROMPT = (
    "Transcribe this audio verbatim for a knowledge indexing pipeline. "
    "Return plain text only with paragraph breaks. Do not summarize."
)


def is_podcast_audio_url(source_url: str) -> bool:
    if source_url.startswith(PSEUDO_PODCAST_ENTRY_PREFIX):
        return False
    parsed = urlparse(source_url)
    path = parsed.path.lower()
    if path.endswith(AUDIO_EXTENSIONS):
        return True
    if "episode.flightcast.com" in parsed.netloc.lower():
        return True
    return False


def _audio_suffix(source_url: str, content_type: str = "") -> str:
    path = urlparse(source_url).path.lower()
    for ext in AUDIO_EXTENSIONS:
        if path.endswith(ext):
            return f"audio{ext}"
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip() if content_type else "")
    if guessed in {".mp3", ".m4a", ".wav", ".aac", ".ogg"}:
        return f"audio{guessed}"
    return "audio.mp3"


def download_podcast_audio(source_url: str, persona_id: str, root: Path | None = None) -> tuple[Path, dict[str, str]]:
    base_root = root or project_root()
    response = httpx.get(source_url, timeout=120.0, follow_redirects=True)
    response.raise_for_status()
    headers = {key.lower(): value for key, value in response.headers.items()}
    suffix = _audio_suffix(source_url, headers.get("content-type", ""))
    path = save_raw_bytes(persona_id, source_url, suffix, response.content, base_root)
    return path, headers


def transcribe_audio_with_gemini(audio_path: Path, model: str) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required for podcast transcription")

    from google.genai import types

    client = build_gemini_client(api_key, timeout_ms=300_000)
    audio_bytes = audio_path.read_bytes()
    mime_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"

    if len(audio_bytes) <= INLINE_AUDIO_MAX_BYTES:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=TRANSCRIBE_PROMPT),
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                    ],
                )
            ],
        )
    else:
        uploaded = client.files.upload(file=audio_path)
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=TRANSCRIBE_PROMPT),
                        types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type or mime_type),
                    ],
                )
            ],
        )

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"Gemini returned empty transcript for {audio_path.name}")
    ctx = get_run_context()
    if ctx:
        ctx.record_gemini(
            response=response,
            operation="transcription",
            model=model,
            input_modality="audio",
            metadata={"audio_bytes": len(audio_bytes), "audio_file": audio_path.name},
        )
    return text


def process_podcast(
    persona_id: str,
    source_url: str,
    root: Path | None = None,
    *,
    transcription_model: str = "gemini-2.5-flash",
    title: str = "",
) -> ProcessedDocument:
    if not is_podcast_audio_url(source_url):
        raise ValueError(f"Not a direct podcast audio URL: {source_url}")

    base_root = root or project_root()
    audio_path, headers = download_podcast_audio(source_url, persona_id, base_root)
    transcript = transcribe_audio_with_gemini(audio_path, transcription_model)

    metadata = {
        "source_url": source_url,
        "audio_path": str(audio_path),
        "content_type": headers.get("content-type", ""),
        "transcription_model": transcription_model,
        "title": title or source_url,
    }
    save_json_metadata(persona_id, source_url, metadata, base_root)

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "document.txt").write_text(transcript, encoding="utf-8")
    (processed_dir / "transcript.txt").write_text(transcript, encoding="utf-8")

    doc_title = title or _title_from_url(source_url)
    return ProcessedDocument(
        title=doc_title,
        text=transcript,
        source_nature=SourceNature.NATURAL_SPOKEN,
        metadata=metadata,
    )


def _title_from_url(source_url: str) -> str:
    path = urlparse(source_url).path
    name = Path(path).name
    if name:
        return re.sub(r"\.[a-z0-9]+$", "", name, flags=re.IGNORECASE)
    return source_url
