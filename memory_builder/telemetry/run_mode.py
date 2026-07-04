from __future__ import annotations

from typing import Any

DISCOVERY_STAGE = "discovery"
PROCESSING_STAGES = (
    "source_start",
    "source_fetch",
    "source_extract",
    "source_index",
    "source_done",
    "source_skip",
    "source_error",
)


REPROCESS_MODE = "Transcript újrafeldolgozás"


def describe_run_mode(
    *,
    skip_discovery: bool = False,
    discover_only: bool = False,
    dry_run: bool = False,
    reprocess_transcripts: bool = False,
) -> str:
    if dry_run or discover_only:
        return "Keresés"
    if reprocess_transcripts:
        return REPROCESS_MODE
    if skip_discovery:
        return "Feldolgozás"
    return "Keresés + feldolgozás"


def resolve_run_mode(
    *,
    options: dict[str, Any] | None,
    sources_discovered: int,
    sources_processed: int,
    had_discovery: bool = False,
    had_processing: bool = False,
    had_run_started: bool = False,
) -> str:
    if options:
        return describe_run_mode(
            skip_discovery=bool(options.get("skip_discovery")),
            discover_only=bool(options.get("discover_only")),
            dry_run=bool(options.get("dry_run")),
            reprocess_transcripts=bool(options.get("reprocess_transcripts")),
        )

    discovered = sources_discovered > 0 or had_discovery
    processed = sources_processed > 0 or had_processing

    if discovered and processed:
        return "Keresés + feldolgozás"
    if discovered:
        return "Keresés"
    if processed:
        return "Feldolgozás"
    if had_run_started:
        return "Feldolgozás"
    return "—"
