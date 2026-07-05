#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.env import load_project_env

load_project_env()

from memory_builder.cli.pipeline_args import add_pipeline_run_arguments
from memory_builder.pipeline.initial_build import MemoryPipeline
from memory_builder.pipeline.fatal_errors import PipelineCancelledError, PipelineFatalError
from memory_builder.source_gate import ensure_sources_approved
from memory_builder.source_review import print_approved_summary
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.telemetry.context import PipelineRunContext, run_context
from memory_builder.telemetry.queries import get_cost_totals


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build persona memory from seed and watch sources.")
    parser.add_argument("--persona", default="hormozi", help="Persona id")
    parser.add_argument("--limit", type=int, default=None, help="Max pending sources to process")
    parser.add_argument("--dry-run", action="store_true", help="Discover sources only")
    parser.add_argument("--retry-failed", action="store_true", help="Reset failed sources to pending and reprocess")
    add_pipeline_run_arguments(parser)
    parser.add_argument(
        "--skip-source-review",
        action="store_true",
        help="Skip approved profile source gate (not recommended)",
    )
    parser.add_argument(
        "--profiles-only",
        action="store_true",
        help="Verify approved profile sources and exit (no content discovery/build)",
    )
    return parser.parse_args(argv)


def _build_pipeline(args: argparse.Namespace) -> MemoryPipeline:
    return MemoryPipeline(
        args.persona,
        ROOT,
        limit=args.limit,
        dry_run=args.dry_run,
        only_platform=args.only,
        media_format=args.media,
        skip_discovery=args.skip_discovery,
        discovery_limit=args.discovery_limit,
        reprocess_transcripts=args.reprocess_transcripts,
    )


def _print_summary(args: argparse.Namespace, summary, run_id: int | None, cost_usd: float | None) -> None:
    only_suffix = f" only={args.only}" if args.only else ""
    if run_id is not None and cost_usd is not None:
        print(
            f"run={run_id}{only_suffix} discovered={summary.sources_discovered} processed={summary.sources_processed} "
            f"skipped_unchanged={summary.sources_skipped_unchanged} updated={summary.sources_updated} "
            f"units={summary.units_created} duplicate={summary.units_skipped_duplicate} "
            f"repeated={summary.units_repeated_idea} clarification={summary.units_clarification} errors={summary.errors} "
            f"cost_usd={cost_usd:.6f}"
        )
    else:
        print(
            f"discovered={summary.sources_discovered} processed={summary.sources_processed}{only_suffix} "
            f"skipped_unchanged={summary.sources_skipped_unchanged} updated={summary.sources_updated} "
            f"units={summary.units_created} duplicate={summary.units_skipped_duplicate} "
            f"repeated={summary.units_repeated_idea} clarification={summary.units_clarification} errors={summary.errors}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    gate_status = ensure_sources_approved(args.persona, skip=args.skip_source_review)
    if gate_status != 0:
        return gate_status
    if args.profiles_only:
        print_approved_summary(args.persona)
        return 0
    store = SQLiteStore(args.persona, ROOT)
    store.initialize()
    run_id: int | None = None
    if not args.dry_run:
        run_id = store.start_sync_run()
        store.set_run_pid(run_id, os.getpid())
    run_options = {
        "skip_discovery": args.skip_discovery or args.reprocess_transcripts,
        "discover_only": args.discover_only,
        "retry_failed": args.retry_failed,
        "reprocess_transcripts": args.reprocess_transcripts,
        "only_platform": args.only or "",
        "dry_run": args.dry_run,
    }
    ctx = PipelineRunContext(args.persona, run_id or 0, store, run_options=run_options) if run_id else None
    pipeline = _build_pipeline(args)
    try:
        if ctx:
            with run_context(ctx):
                pipeline.run_initial_build(
                    retry_failed=args.retry_failed,
                    discover_only=args.discover_only,
                )
        else:
            pipeline.run_initial_build(
                retry_failed=args.retry_failed,
                discover_only=args.discover_only,
            )
    except (PipelineFatalError, PipelineCancelledError):
        pass
    summary = pipeline.summary
    cost_usd: float | None = None
    if run_id and store.is_run_open(run_id):
        store.finish_sync_run(run_id, pipeline.summary_dict())
        cost_usd = get_cost_totals(store, args.persona, run_id=run_id).cost_usd
    elif run_id:
        cost_usd = get_cost_totals(store, args.persona, run_id=run_id).cost_usd
    store.close()
    _print_summary(args, summary, run_id, cost_usd)
    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
