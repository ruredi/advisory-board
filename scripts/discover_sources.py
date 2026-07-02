#!/usr/bin/env python3
"""Discover candidate official profile sources for persona review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.env import load_project_env
from memory_builder.source_review import format_candidate_line, run_discovery


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover persona profile source candidates.")
    parser.add_argument("--persona", default="hormozi", help="Persona id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    candidates = run_discovery(args.persona)
    print(f"\n=== Discovered {len(candidates)} candidates for {args.persona} ===\n")
    for index, candidate in enumerate(candidates, start=1):
        print(format_candidate_line(index, candidate))
        print()
    print("Next: python3 scripts/review_sources.py --persona", args.persona)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
