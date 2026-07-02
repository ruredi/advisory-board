from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.source_registry import approved_path, is_sources_approved


def ensure_sources_approved(persona_id: str, *, skip: bool = False) -> int:
    if skip:
        return 0
    if is_sources_approved(persona_id):
        return 0
    print("ERROR: Profile sources have not been reviewed yet.", file=sys.stderr)
    print(file=sys.stderr)
    print("Run:", file=sys.stderr)
    print(f"  python3 scripts/discover_sources.py --persona {persona_id}", file=sys.stderr)
    print(f"  python3 scripts/review_sources.py --persona {persona_id}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"Expected output: {approved_path(persona_id)}", file=sys.stderr)
    return 2
