from __future__ import annotations

import argparse

from memory_builder.pipeline.platform_filter import SUPPORTED_PLATFORMS


def add_pipeline_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--only",
        choices=sorted(SUPPORTED_PLATFORMS),
        default=None,
        help="Process only this platform (youtube, spotify, x, instagram, web)",
    )
    parser.add_argument(
        "--skip-discovery",
        action="store_true",
        help="Skip source discovery; only process existing pending/failed sources",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Discover and save new sources only; do not process pending sources",
    )
    parser.add_argument(
        "--discovery-limit",
        type=int,
        default=None,
        help="Max new sources to discover (0 = unlimited). Default: unlimited for discover-only, 50 otherwise",
    )
    parser.add_argument(
        "--reprocess-transcripts",
        action="store_true",
        help=(
            "Re-diarize and re-index indexed YouTube/podcast sources only "
            "(skips discovery and other pending sources)"
        ),
    )
    parser.add_argument(
        "--source-ids",
        type=str,
        default=None,
        help="Comma-separated source IDs to process (skips discovery and other pending sources)",
    )
