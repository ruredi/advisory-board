#!/usr/bin/env python3
"""Backfill the sources.media_format column for existing sources.

Determines the primary media modality (text / image / video / audio) for each
source that is still 'unknown'. Social posts are classified from the scraped
`social.json` payload; everything else from the source type / URL.

Usage:
    python3 scripts/backfill_media_format.py                 # all personas
    python3 scripts/backfill_media_format.py --persona hormozi
    python3 scripts/backfill_media_format.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.discovery.seed_links import infer_media_format
from memory_builder.fetch.downloader import source_slug
from memory_builder.models import MediaFormat
from memory_builder.paths import memory_dir, sources_raw_dir
from memory_builder.processors.social_media_enrichment import (
    classify_social_media_format,
    instagram_media_format,
    tweet_media_format,
)


def _social_media_format(persona_id: str, source_url: str) -> str | None:
    slug = source_slug(source_url)
    social_path = sources_raw_dir(persona_id, ROOT) / slug / "social.json"
    if not social_path.exists():
        return None
    try:
        payload = json.loads(social_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    stored = payload.get("media_format")
    if isinstance(stored, str) and stored and stored != MediaFormat.UNKNOWN:
        return stored
    platform = str(payload.get("platform") or "")
    post = payload.get("post")
    tweet = payload.get("tweet")
    if platform == "instagram" and isinstance(post, dict):
        return instagram_media_format(post)
    if platform == "x" and isinstance(tweet, dict):
        return tweet_media_format(tweet, source_url)
    if platform == "facebook":
        has_text = bool(post.get("text")) if isinstance(post, dict) else False
        return classify_social_media_format(
            has_video="/reel" in source_url.lower() or "/videos/" in source_url.lower(),
            has_images=False,
            has_text=has_text,
        )
    return None


def _resolve_media_format(persona_id: str, source_type: str, source_url: str) -> str:
    if source_type == "social":
        social = _social_media_format(persona_id, source_url)
        if social and social != MediaFormat.UNKNOWN:
            return social
    return infer_media_format(source_type, source_url)


def backfill_persona(db_file: Path, *, dry_run: bool) -> tuple[int, dict[str, int]]:
    persona_id = db_file.stem
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    has_sources = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sources' LIMIT 1"
    ).fetchone()
    if not has_sources:
        conn.close()
        return -1, {}
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
    if "media_format" not in columns:
        conn.execute("ALTER TABLE sources ADD COLUMN media_format TEXT NOT NULL DEFAULT 'unknown'")
        conn.commit()
    rows = conn.execute(
        "SELECT id, source_type, source_url FROM sources "
        "WHERE persona_id = ? AND (media_format IS NULL OR media_format = 'unknown')",
        (persona_id,),
    ).fetchall()
    updated = 0
    counts: dict[str, int] = {}
    for row in rows:
        media_format = _resolve_media_format(persona_id, str(row["source_type"]), str(row["source_url"]))
        if media_format == MediaFormat.UNKNOWN:
            continue
        counts[media_format] = counts.get(media_format, 0) + 1
        updated += 1
        if not dry_run:
            conn.execute(
                "UPDATE sources SET media_format = ? WHERE id = ?",
                (media_format, int(row["id"])),
            )
    if not dry_run:
        conn.commit()
    conn.close()
    return updated, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill sources.media_format.")
    parser.add_argument("--persona", default=None, help="Persona id (default: all personas)")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    db_dir = memory_dir(ROOT)
    if args.persona:
        db_files = [db_dir / f"{args.persona}.sqlite"]
    else:
        db_files = sorted(db_dir.glob("*.sqlite"))

    total = 0
    for db_file in db_files:
        if not db_file.exists():
            print(f"skip (missing): {db_file.name}")
            continue
        updated, counts = backfill_persona(db_file, dry_run=args.dry_run)
        if updated < 0:
            print(f"skip (no sources table): {db_file.name}")
            continue
        total += updated
        breakdown = ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "—"
        prefix = "[dry-run] " if args.dry_run else ""
        print(f"{prefix}{db_file.stem}: updated={updated} ({breakdown})")
    print(f"{'[dry-run] ' if args.dry_run else ''}total_updated={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
