#!/usr/bin/env python3
"""Live smoke test: download one podcast MP3 and transcribe with Gemini."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.env import load_project_env

load_project_env()

import feedparser

from memory_builder.config import load_persona_config
from memory_builder.processors.podcast_transcript import (
    download_podcast_audio,
    is_podcast_audio_url,
    process_podcast,
    transcribe_audio_with_gemini,
)


def latest_mp3_from_rss(rss_url: str) -> tuple[str, str]:
    parsed = feedparser.parse(rss_url)
    for entry in parsed.entries[:5]:
        title = getattr(entry, "title", "") or "episode"
        for link in getattr(entry, "links", []) or []:
            href = link.get("href", "")
            if href and link.get("rel") == "enclosure" and is_podcast_audio_url(href):
                return href, title
    raise RuntimeError(f"No MP3 enclosure found in RSS: {rss_url}")


def clip_audio(audio_path: Path, seconds: int) -> Path:
    if seconds <= 0:
        return audio_path
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("--clip-seconds requires ffmpeg on PATH")
    clipped = Path(tempfile.mkstemp(suffix=".mp3")[1])
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-t",
            str(seconds),
            "-acodec",
            "copy",
            str(clipped),
        ],
        check=True,
        capture_output=True,
    )
    return clipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Podcast transcript smoke test")
    parser.add_argument("--persona", default="hormozi")
    parser.add_argument(
        "--rss",
        default="https://rss2.flightcast.com/zz5nwp81tktx53wb8fw6qq7j.xml",
        help="Podcast RSS feed URL",
    )
    parser.add_argument("--url", default="", help="Direct MP3 URL (skips RSS lookup)")
    parser.add_argument("--title", default="", help="Episode title for --url")
    parser.add_argument("--model", default="", help="Gemini model (default: persona transcription_model)")
    parser.add_argument(
        "--clip-seconds",
        type=int,
        default=0,
        help="Transcribe only the first N seconds (requires ffmpeg; good for quick smoke)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download MP3 only; skip Gemini transcription",
    )
    parser.add_argument(
        "--diarized",
        action="store_true",
        help="Use persona speaker_labeled_transcription config for diarized Gemini output",
    )
    args = parser.parse_args()

    config = load_persona_config(args.persona)
    model = args.model or config.transcription_model
    use_diarized = args.diarized or config.speaker_labeled_transcription

    if args.url:
        mp3_url, title = args.url, args.title or args.url
    else:
        mp3_url, title = latest_mp3_from_rss(args.rss)

    print(f"MP3: {mp3_url}")
    print(f"Title: {title}")
    print(f"Model: {model}")

    if args.download_only:
        audio_path, headers = download_podcast_audio(mp3_url, args.persona)
        print(f"Downloaded: {audio_path} ({len(headers)} headers)")
        return 0

    if args.clip_seconds > 0:
        audio_path, _headers = download_podcast_audio(mp3_url, args.persona)
        clipped = clip_audio(audio_path, args.clip_seconds)
        try:
            transcript = transcribe_audio_with_gemini(clipped, model)
        finally:
            if clipped != audio_path and clipped.exists():
                clipped.unlink()
        preview = transcript.replace("\n", " ")[:200]
        print(f"OK  transcript chars={len(transcript)} (clip {args.clip_seconds}s)")
        print(f"Preview: {preview}...")
        return 0

    doc = process_podcast(
        args.persona,
        mp3_url,
        title=title,
        transcription_model=model,
        display_name=config.display_name,
        speaker_names=config.speaker_names,
        speaker_labeled_transcription=use_diarized,
    )
    preview = doc.text.replace("\n", " ")[:200]
    print(f"OK  transcript chars={len(doc.text)} mode={doc.metadata.get('transcription_mode', 'unknown')}")
    if doc.metadata.get("segment_count") is not None:
        print(f"segments={doc.metadata.get('segment_count')} target={doc.metadata.get('target_segment_count')}")
    print(f"Preview: {preview}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
