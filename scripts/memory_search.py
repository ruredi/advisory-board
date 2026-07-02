#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.retrieval.context_pack import MemorySearch, build_context_pack


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search persona memory.")
    parser.add_argument("persona", help="Persona id")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--context-pack", action="store_true", help="Print prompt-ready context pack")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    query = " ".join(args.query)
    if args.context_pack:
        print(build_context_pack(args.persona, query, root=ROOT, top_k=args.top_k))
        return 0
    search = MemorySearch(args.persona, root=ROOT, top_k=args.top_k)
    hits = search.search(query)
    if not hits:
        print("No results.")
        return 0
    for hit in hits:
        print(f"[{hit.score:.3f}] #{hit.unit_id} {hit.content_type} — {hit.source_title}")
        print(hit.chunk_text[:400])
        if hit.steps:
            print("Steps:", " | ".join(hit.steps))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
