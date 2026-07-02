from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.channel_registry import add_channel, load_channels, save_channels
from memory_builder.config import load_persona_config
from memory_builder.discovery.channel_feeds import discover_channels
from memory_builder.discovery.podcast_rss import resolve_apple_podcast_rss, resolve_spotify_show_rss
from memory_builder.env import load_project_env
from memory_builder.pipeline.initial_build import MemoryPipeline


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a content channel (YouTube, Spotify, podcast RSS).")
    parser.add_argument("--persona", default="hormozi", help="Persona id")
    parser.add_argument(
        "--type",
        required=True,
        choices=("youtube_channel", "spotify_show", "apple_podcast", "podcast_rss"),
        help="Channel type",
    )
    parser.add_argument("--url", required=True, help="Channel URL")
    parser.add_argument("--label", default="", help="Human-readable label")
    parser.add_argument("--rss-url", default="", help="Optional RSS URL override")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Discover new episodes from this channel and process pending sources",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max sources to process after discovery")
    return parser.parse_args(argv)


def resolve_channel_rss(channel_type: str, url: str, label: str, rss_override: str) -> tuple[str | None, str | None]:
    if rss_override:
        return rss_override, None
    if channel_type == "podcast_rss":
        return url, None
    if channel_type == "apple_podcast":
        return resolve_apple_podcast_rss(url)
    if channel_type == "spotify_show":
        return resolve_spotify_show_rss(url, search_term=label or None)
    return None, None


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    load_persona_config(args.persona)

    rss_url, apple_podcast_id = resolve_channel_rss(args.type, args.url, args.label, args.rss_url.strip())
    if args.type in {"spotify_show", "apple_podcast", "podcast_rss"} and not rss_url:
        print("ERROR: Could not resolve podcast RSS feed for this URL.", file=sys.stderr)
        return 1

    channel = add_channel(
        args.persona,
        channel_type=args.type,
        url=args.url,
        label=args.label or args.url,
        rss_url=rss_url,
        apple_podcast_id=apple_podcast_id,
    )
    print(f"Added channel: {channel.channel_id}")
    print(f"  type: {channel.type}")
    print(f"  url:  {channel.url}")
    if channel.rss_url:
        print(f"  rss:  {channel.rss_url}")

    if not args.sync:
        print("\nNext: python3 scripts/memory_sync.py --persona", args.persona)
        return 0

    registry = load_channels(args.persona)
    pipeline = MemoryPipeline(args.persona, limit=args.limit)
    pipeline.initialize()
    records = discover_channels(
        args.persona,
        registry,
        channel_ids=[channel.channel_id],
        store=pipeline.store,
    )
    save_channels(registry)
    pipeline.summary.sources_discovered = len(records)
    if not pipeline.dry_run:
        for record in records:
            from memory_builder.dedup.title_dedup import normalize_episode_title

            record.normalized_title = normalize_episode_title(record.source_title)
            pipeline.store.upsert_source(record)
        pipeline.process_pending()
    print(
        f"discovered={pipeline.summary.sources_discovered} processed={pipeline.summary.sources_processed} "
        f"skipped_unchanged={pipeline.summary.sources_skipped_unchanged} errors={pipeline.summary.errors}"
    )
    return 0 if pipeline.summary.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
