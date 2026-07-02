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
