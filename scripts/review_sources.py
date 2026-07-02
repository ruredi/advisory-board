#!/usr/bin/env python3
"""Interactive review of discovered persona profile sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.env import load_project_env
from memory_builder.source_review import interactive_review


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review persona profile source candidates.")
    parser.add_argument("--persona", default="hormozi", help="Persona id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    interactive_review(args.persona)
    print("\nNext: python3 scripts/memory_build.py --persona", args.persona, "--profiles-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
