from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from memory_builder.fetch.downloader import save_json_metadata, source_slug
from memory_builder.models import ProcessedDocument, SourceNature
from memory_builder.paths import project_root, sources_processed_dir, sources_raw_dir
from memory_builder.processors.transcript_pipeline import build_diarized_document_text


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


def process_youtube(
    persona_id: str,
    source_url: str,
    root: Path | None = None,
    *,
    transcription_model: str = "gemini-2.5-flash",
    display_name: str = "",
    speaker_names: list[str] | None = None,
    speaker_labeled_transcription: bool = False,
    allow_unlabeled_fallback: bool = False,
) -> ProcessedDocument:
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

    raw_dir = sources_raw_dir(persona_id, base_root) / source_slug(source_url)
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "title": title,
        "video_id": video_id,
        "upload_date": upload_date,
        "source_url": source_url,
        "display_name": display_name,
        "speaker_names": speaker_names or [],
    }

    if speaker_labeled_transcription and display_name:
        try:
            audio_path = _download_youtube_audio(video_id, raw_dir)
            extraction_input, segments, artifact_paths = build_diarized_document_text(
                audio_path=audio_path,
                transcription_model=transcription_model,
                display_name=display_name,
                speaker_names=speaker_names or [],
                processed_dir=processed_dir,
            )
            metadata.update(
                {
                    "transcription_mode": "diarized",
                    "audio_path": str(audio_path),
                    "segment_count": len(segments.segments),
                    "target_segment_count": sum(
                        1 for segment in segments.segments if segment.speaker_type == "target"
                    ),
                    **{f"path_{key}": value for key, value in artifact_paths.items()},
                }
            )
            transcript = extraction_input
        except Exception as exc:
            if not allow_unlabeled_fallback:
                raise RuntimeError(f"YouTube diarized transcription failed: {exc}") from exc
            transcript = _fetch_youtube_transcript(video_id)
            metadata["transcription_mode"] = "fallback_vtt"
            metadata["diarization_error"] = str(exc)
            _write_plain_transcript(processed_dir, raw_dir, transcript)
    else:
        transcript = _fetch_youtube_transcript(video_id)
        metadata["transcription_mode"] = "plain_vtt"
        _write_plain_transcript(processed_dir, raw_dir, transcript)

    save_json_metadata(persona_id, source_url, metadata, base_root)
    nature = (
        SourceNature.PERFORMED_SPOKEN
        if any(token in title.lower() for token in ("keynote", "speech"))
        else SourceNature.NATURAL_SPOKEN
    )
    return ProcessedDocument(
        title=title,
        text=transcript,
        source_nature=nature,
        metadata=metadata,
    )


def _write_plain_transcript(processed_dir: Path, raw_dir: Path, transcript: str) -> None:
    (raw_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
    (processed_dir / "document.txt").write_text(transcript, encoding="utf-8")
    (processed_dir / "transcript.txt").write_text(transcript, encoding="utf-8")


def _download_youtube_audio(video_id: str, raw_dir: Path) -> Path:
    output_template = str(raw_dir / "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "m4a",
        "--output",
        output_template,
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "yt-dlp audio download failed")
    candidates = sorted(raw_dir.glob("audio.*"))
    if not candidates:
        raise RuntimeError(f"No downloaded audio file for video {video_id}")
    return candidates[0]


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
