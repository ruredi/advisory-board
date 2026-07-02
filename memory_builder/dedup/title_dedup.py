from __future__ import annotations

import re
import sqlite3

from memory_builder.models import SourceStatus, SourceType


EPISODE_NUMBER_PATTERN = re.compile(
    r"(?:\||-)\s*ep(?:isode)?\.?\s*\d+|\bep(?:isode)?\.?\s*\d+\b",
    re.IGNORECASE,
)


def normalize_episode_title(title: str) -> str:
    cleaned = title.strip().lower()
    cleaned = EPISODE_NUMBER_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def titles_likely_match(left: str, right: str) -> bool:
    left_norm = normalize_episode_title(left)
    right_norm = normalize_episode_title(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm:
        return True
    shorter, longer = sorted((left_norm, right_norm), key=len)
    if len(shorter) < 20:
        return False
    return shorter in longer


def find_matching_youtube_source(
    conn: sqlite3.Connection,
    persona_id: str,
    podcast_title: str,
) -> sqlite3.Row | None:
    rows = conn.execute(
        """
        SELECT * FROM sources
        WHERE persona_id = ?
          AND source_type = ?
          AND status IN (?, ?)
        """,
        (persona_id, SourceType.YOUTUBE, SourceStatus.INDEXED, SourceStatus.PROCESSED),
    ).fetchall()
    for row in rows:
        if titles_likely_match(podcast_title, row["source_title"]):
            return row
    return None


def should_skip_podcast_for_youtube_duplicate(
    conn: sqlite3.Connection,
    persona_id: str,
    podcast_title: str,
) -> tuple[bool, str | None]:
    match = find_matching_youtube_source(conn, persona_id, podcast_title)
    if match is None:
        return False, None
    return True, f"YouTube duplicate already indexed: {match['source_title']} ({match['source_url']})"
