from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments


SPEAKER_LINE_RE = re.compile(r"^(?P<speaker>.+?):\s*(?P<text>.*)$", flags=re.MULTILINE)
MAX_SPEAKER_LABEL_LEN = 80
TIMESTAMP_IN_LABEL_RE = re.compile(r"\d{1,2}:\d{2}")
METRIC_LABEL_RE = re.compile(r"^(replies|retweets|likes|views|bookmarks)\b", re.IGNORECASE)
WEEKDAY_PREFIX_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", re.IGNORECASE)


def looks_like_speaker_label(speaker: str) -> bool:
    stripped = speaker.strip()
    if not stripped or len(stripped) > MAX_SPEAKER_LABEL_LEN:
        return False
    if TIMESTAMP_IN_LABEL_RE.search(stripped):
        return False
    if METRIC_LABEL_RE.match(stripped):
        return False
    if WEEKDAY_PREFIX_RE.match(stripped):
        return False
    return True


@dataclass
class QuoteOrigin:
    segment_id: str
    speaker: str
    speaker_type: str
    text: str
    start_seconds: float | None
    end_seconds: float | None
    source_url: str
    source_title: str
    source_link: str


def is_labeled_transcript(text: str) -> bool:
    if not text.strip():
        return False
    matches = [
        match
        for match in SPEAKER_LINE_RE.finditer(text)
        if looks_like_speaker_label(match.group("speaker"))
    ]
    return len(matches) >= 2


def extract_target_segments(segments: TranscriptSegments) -> str:
    blocks = [segment.text.strip() for segment in segments.segments if segment.speaker_type == "target" and segment.text.strip()]
    return "\n\n".join(blocks)


def build_extraction_input(segments: TranscriptSegments) -> str:
    blocks: list[str] = []
    for segment in segments.segments:
        text = segment.text.strip()
        if not text:
            continue
        if segment.speaker_type == "target":
            blocks.append(f"[{segment.speaker}]\n{text}")
        else:
            blocks.append(f"[CONTEXT_ONLY - {segment.speaker}]\n{text}")
    return "\n\n".join(blocks)


def build_source_link(source_url: str, start_seconds: float | None) -> str:
    if start_seconds is None:
        return source_url
    parsed = urlparse(source_url)
    if "youtube.com" in parsed.netloc or parsed.netloc.endswith("youtu.be"):
        query = parse_qs(parsed.query)
        query["t"] = [str(int(start_seconds))]
        new_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))
    return source_url


def quote_origin_for_text(
    quote_text: str,
    segments: TranscriptSegments,
    *,
    source_url: str,
    source_title: str,
) -> QuoteOrigin | None:
    normalized = _normalize_quote(quote_text)
    if not normalized:
        return None
    for segment in segments.segments:
        if segment.speaker_type != "target":
            continue
        if normalized not in _normalize_quote(segment.text):
            continue
        source_link = build_source_link(source_url, segment.start_seconds)
        return QuoteOrigin(
            segment_id=segment.segment_id,
            speaker=segment.speaker,
            speaker_type=segment.speaker_type,
            text=segment.text,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            source_url=source_url,
            source_title=source_title,
            source_link=source_link,
        )
    return None


def enrich_quote(
    quote: dict[str, Any],
    *,
    display_name: str,
    speaker_names: list[str],
    segments: TranscriptSegments | None,
    source_url: str,
    source_title: str,
) -> dict[str, Any] | None:
    quote_text = str(quote.get("text", "")).strip()
    if not quote_text or not quote.get("is_verbatim"):
        return None
    speaker = str(quote.get("speaker", "")).strip()
    if not _speaker_matches_persona(speaker, display_name, speaker_names):
        return None
    if segments is None:
        return {
            **quote,
            "speaker": display_name,
            "source_url": source_url,
            "source_title": source_title,
            "source_link": source_url,
        }
    origin = quote_origin_for_text(
        quote_text,
        segments,
        source_url=source_url,
        source_title=source_title,
    )
    if origin is None:
        return None
    return {
        **quote,
        "speaker": display_name,
        "source_url": origin.source_url,
        "source_title": origin.source_title,
        "segment_id": origin.segment_id,
        "start_seconds": origin.start_seconds,
        "end_seconds": origin.end_seconds,
        "source_link": origin.source_link,
    }


def filter_speaker_content_labeled(text: str, display_name: str, speaker_names: list[str]) -> str:
    if not is_labeled_transcript(text):
        return text
    target_labels = {display_name.lower(), *[name.lower() for name in speaker_names]}
    blocks: list[str] = []
    current_label = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        match = SPEAKER_LINE_RE.match(line)
        if match:
            if current_lines and current_label.lower() in target_labels:
                blocks.append("\n".join(current_lines).strip())
            current_label = match.group("speaker").strip()
            current_lines = [match.group("text").strip()] if match.group("text").strip() else []
            continue
        if current_lines is not None and line.strip():
            current_lines.append(line.strip())
    if current_lines and current_label.lower() in target_labels:
        blocks.append("\n".join(current_lines).strip())
    return "\n\n".join(block for block in blocks if block)


def _speaker_matches_persona(speaker: str, display_name: str, speaker_names: list[str]) -> bool:
    lowered = speaker.lower()
    candidates = {display_name.lower(), *[name.lower() for name in speaker_names]}
    return lowered in candidates


def _normalize_quote(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())
