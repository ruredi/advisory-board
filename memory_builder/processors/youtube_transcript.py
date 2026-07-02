from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from memory_builder.fetch.downloader import save_json_metadata, save_raw_bytes, source_slug
from memory_builder.models import ProcessedDocument, SourceNature
from memory_builder.paths import sources_processed_dir, sources_raw_dir


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.lstrip("/").split("/")[0]
    if "youtube.com" in parsed.netloc:
        if parsed.path.startswith("/watch"):
            return parse_qs(parsed.query).get("v", [None])[0]
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in {"shorts", "live"}:
            return parts[1]
    return None


def process_youtube(persona_id: str, source_url: str, root: Path | None = None) -> ProcessedDocument:
    from memory_builder.paths import project_root

    base_root = root or project_root()
    video_id = youtube_video_id(source_url)
    if not video_id:
        raise ValueError(f"Could not parse YouTube video id from {source_url}")

    meta_cmd = [
        "yt-dlp",
        "--skip-download",
        "--dump-json",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    completed = subprocess.run(meta_cmd, capture_output=True, text=True, check=False)
    title = source_url
    upload_date = None
    if completed.returncode == 0 and completed.stdout.strip():
        info = json.loads(completed.stdout.strip().splitlines()[0])
        title = info.get("title", title)
        upload_date = info.get("upload_date")

    transcript = _fetch_youtube_transcript(video_id)
    raw_dir = sources_raw_dir(persona_id, base_root) / source_slug(source_url)
    raw_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = raw_dir / "transcript.txt"
    transcript_path.write_text(transcript, encoding="utf-8")
    save_json_metadata(
        persona_id,
        source_url,
        {"title": title, "video_id": video_id, "upload_date": upload_date},
        base_root,
    )

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "document.txt").write_text(transcript, encoding="utf-8")

    nature = SourceNature.PERFORMED_SPOKEN if any(token in title.lower() for token in ("keynote", "speech")) else SourceNature.NATURAL_SPOKEN
    return ProcessedDocument(
        title=title,
        text=transcript,
        source_nature=nature,
        metadata={"video_id": video_id, "upload_date": upload_date, "source_url": source_url},
    )


def _fetch_youtube_transcript(video_id: str) -> str:
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang",
        "en.*,en",
        "--sub-format",
        "vtt",
        "--output",
        f"/tmp/yt_{video_id}",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)
    candidates = sorted(Path("/tmp").glob(f"yt_{video_id}*.vtt"))
    if not candidates:
        desc_cmd = [
            "yt-dlp",
            "--skip-download",
            "--print",
            "description",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        completed = subprocess.run(desc_cmd, capture_output=True, text=True, check=False)
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
        raise RuntimeError(f"No transcript available for video {video_id}")
    return _vtt_to_text(candidates[0].read_text(encoding="utf-8", errors="ignore"))


def _vtt_to_text(vtt_content: str) -> str:
    lines: list[str] = []
    for line in vtt_content.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or re.fullmatch(r"\d+", line):
            continue
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return "\n".join(lines)
