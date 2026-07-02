#!/usr/bin/env python3
"""Local direct-advisor runner for Advisory Board.

This is intentionally thin: it reads a stable advisor profile, wraps the user
question in governance instructions, and delegates the answer to Hermes with a
safe toolset. Advisor profiles are not allowed to self-modify or create skills.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


class AdvisorProfile(NamedTuple):
    advisor_id: str
    path: Path
    content: str


ROOT = Path(__file__).resolve().parents[1]


def advisors_dir(root: Path = ROOT) -> Path:
    return root / "advisors"


def advisor_path(root: Path, advisor_id: str) -> Path:
    normalized = advisor_id.strip().lower().replace("_", "-")
    aliases = {
        "steve-jobs": "jobs",
        "warren-buffett": "buffett",
        "elon-musk": "musk",
        "alex-hormozi": "hormozi",
        "peter-thiel": "thiel",
        "jeff-bezos": "bezos",
    }
    canonical = aliases.get(normalized, normalized)
    return advisors_dir(root) / f"{canonical}.md"


def list_advisors(root: Path = ROOT) -> list[str]:
    directory = advisors_dir(root)
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.md") if not path.name.startswith("_"))


def load_profile(root: Path, advisor_id: str) -> AdvisorProfile:
    path = advisor_path(root, advisor_id)
    if not path.exists():
        available = ", ".join(list_advisors(root)) or "none"
        raise SystemExit(f"Unknown advisor '{advisor_id}'. Available advisors: {available}")
    return AdvisorProfile(advisor_id=path.stem, path=path, content=path.read_text(encoding="utf-8"))


def build_prompt(profile: AdvisorProfile, question: str, *, mode: str = "quick", memory_context: str | None = None) -> str:
    memory_block = ""
    if mode == "research_grounded":
        memory_block = f"""
--- SOURCE-BACKED MEMORY START ---
{(memory_context or "No indexed source-backed memory was retrieved for this question.").strip()}
--- SOURCE-BACKED MEMORY END ---

Memory rules for this answer:
- Use indexed source-backed memory for evidence, examples, frameworks, process steps, and quotes.
- Do not invent quotes, book references, podcast lines, or process steps that are not in the memory block.
- If memory is weak or missing, say that clearly and answer with judgment without fake citations.
- Verbatim quotes only when the memory block marks them as quotes.
"""
    return f"""You are running one direct Advisory Board advisor session.

Use the advisor profile below as the full personality contract.
Answer as a stable advisory lens, not as an autonomous agent.
Do not claim to be the real person; this is a decision framework inspired by public thinking patterns.
You must not create, edit, install, or suggest installing skills.
You must not rewrite your own prompt, update your own memory/source policy, or start self-development.
If the question reveals a weakness in the profile, mention it as feedback for an external maintainer; do not apply the change yourself.
Do not execute tasks. Give advice only.
{memory_block}
--- ADVISOR PROFILE START ---
{profile.content.strip()}
--- ADVISOR PROFILE END ---

Andras's question:
{question.strip()}

Answer in the profile's style. Be concise, opinionated, and practical.
"""


def build_hermes_command(prompt: str) -> list[str]:
    return [
        "hermes",
        "chat",
        "--quiet",
        "--toolsets",
        "safe",
        "--ignore-rules",
        "--source",
        "advisory-board",
        "-q",
        prompt,
    ]


def run_advisor(
    advisor_id: str,
    question: str,
    *,
    root: Path = ROOT,
    dry_run: bool = False,
    mode: str = "quick",
) -> int:
    profile = load_profile(root, advisor_id)
    memory_context = None
    if mode == "research_grounded":
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from memory_builder.retrieval.context_pack import build_context_pack

        memory_context = build_context_pack(profile.advisor_id, question, root=root)
    prompt = build_prompt(profile, question, mode=mode, memory_context=memory_context)
    if dry_run:
        print("DRY RUN — prompt that would be sent to Hermes:\n")
        print(prompt)
        return 0

    command = build_hermes_command(prompt)
    completed = subprocess.run(command, cwd=root, text=True)
    return completed.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask one Advisory Board advisor directly.")
    parser.add_argument("advisor", nargs="?", help="Advisor id or alias: jobs, buffett, musk, hormozi, thiel, bezos")
    parser.add_argument("question", nargs="*", help="Question to ask the advisor")
    parser.add_argument("--dry-run", action="store_true", help="Print the prompt without calling Hermes")
    parser.add_argument("--list", action="store_true", help="List available advisors and exit")
    parser.add_argument(
        "--mode",
        choices=["quick", "research_grounded"],
        default="quick",
        help="Answer mode; research_grounded retrieves indexed persona memory first",
    )
    args = parser.parse_args(argv)
    if not args.list and (not args.advisor or not args.question):
        parser.error("advisor and question are required unless --list is used")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.list:
        print("\n".join(list_advisors(ROOT)))
        return 0
    return run_advisor(args.advisor, " ".join(args.question), dry_run=args.dry_run, mode=args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
