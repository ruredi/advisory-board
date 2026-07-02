#!/usr/bin/env python3
"""Convenient command router for Advisory Board direct advisor chats.

Supported message forms:
- jobs: What should we cut?
- jobs,buffett: Should we build board mode now?
- /jobs What should we cut?              # terminal/script only; Hermes chat treats leading / as a slash command
- /steve-jobs What should we cut?        # terminal/script only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ask_advisor  # noqa: E402


class Route(NamedTuple):
    advisors: list[str]
    question: str


ALIASES = {
    "jobs": "jobs",
    "job": "jobs",
    "steve": "jobs",
    "steve-jobs": "jobs",
    "steve_jobs": "jobs",
    "buffett": "buffett",
    "buffet": "buffett",
    "warren": "buffett",
    "warren-buffett": "buffett",
    "warren_buffett": "buffett",
    "musk": "musk",
    "elon": "musk",
    "elon-musk": "musk",
    "elon_musk": "musk",
    "hormozi": "hormozi",
    "alex": "hormozi",
    "alex-hormozi": "hormozi",
    "alex_hormozi": "hormozi",
    "thiel": "thiel",
    "peter": "thiel",
    "peter-thiel": "thiel",
    "peter_thiel": "thiel",
    "bezos": "bezos",
    "jeff": "bezos",
    "jeff-bezos": "bezos",
    "jeff_bezos": "bezos",
}


def normalize_advisor(token: str) -> str:
    key = token.strip().lower().removeprefix("/").removeprefix("@").replace(" ", "-")
    advisor = ALIASES.get(key)
    available = ask_advisor.list_advisors(ROOT)
    if advisor not in available:
        raise SystemExit(f"Unknown advisor '{token}'. Available advisors: {', '.join(available)}")
    return advisor


def parse_advisor_list(raw: str) -> list[str]:
    tokens = [part.strip() for part in raw.replace("+", ",").split(",") if part.strip()]
    if not tokens:
        raise SystemExit("Missing advisor route")

    advisors = []
    for token in tokens:
        advisor = normalize_advisor(token)
        if advisor not in advisors:
            advisors.append(advisor)
    return advisors


def parse_route(message: str) -> Route:
    text = message.strip()
    if not text:
        raise SystemExit("Missing routed message")

    if text.startswith(("/", "@")):
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            raise SystemExit("Missing question after advisor command")
        advisors = parse_advisor_list(parts[0])
        question = parts[1].strip()
    elif ":" in text:
        raw_advisors, raw_question = text.split(":", 1)
        advisors = parse_advisor_list(raw_advisors)
        question = raw_question.strip()
    else:
        raise SystemExit("Route must start with /advisor, @advisor, or advisor: question")

    if not question:
        raise SystemExit("Missing question after advisor command")
    return Route(advisors=advisors, question=question)


def run_route(route: Route, *, dry_run: bool = False) -> int:
    print(f"Route: {', '.join(route.advisors)}", flush=True)
    exit_code = 0
    for index, advisor_id in enumerate(route.advisors):
        if len(route.advisors) > 1:
            if index:
                print(flush=True)
            print(f"=== {advisor_id} ===", flush=True)
        code = ask_advisor.run_advisor(advisor_id, route.question, root=ROOT, dry_run=dry_run)
        if code != 0:
            exit_code = code
            break
    return exit_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route a short command to one or more Advisory Board advisors.")
    parser.add_argument("message", nargs="*", help="Routed message, e.g. 'jobs: What should we cut?' or 'jobs,buffett: Should we ship?'")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling Hermes")
    parser.add_argument("--list", action="store_true", help="List available advisors and command aliases")
    args = parser.parse_args(argv)
    if not args.list and not args.message:
        parser.error("message is required unless --list is used")
    return args


def print_routes() -> None:
    print("Available chat-safe advisor routes:")
    for advisor in ask_advisor.list_advisors(ROOT):
        print(f"{advisor}:")
    print("\nExamples:")
    print('python3 scripts/advisor.py "jobs: What should we cut?"')
    print('python3 scripts/advisor.py "jobs,buffett: Should we build board mode now?"')
    print('python3 scripts/advisor.py "steve-jobs: What should we cut?"')
    print("\nNote: leading-slash forms like /jobs are supported only inside the terminal script argument.")
    print("Do not type /jobs directly into Hermes chat; Hermes will treat it as an unknown slash command.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.list:
        print_routes()
        return 0
    route = parse_route(" ".join(args.message))
    return run_route(route, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
