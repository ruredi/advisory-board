#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ask_advisor  # noqa: E402


class AskAdvisorGroundedTests(unittest.TestCase):
    def test_research_grounded_prompt_contains_memory_and_quote_guard(self) -> None:
        profile = ask_advisor.load_profile(ROOT, "hormozi")
        prompt = ask_advisor.build_prompt(
            profile,
            "How do you diagnose a weak offer?",
            mode="research_grounded",
            memory_context="[1] Sample source\nQuote guard test",
        )
        self.assertIn("SOURCE-BACKED MEMORY START", prompt)
        self.assertIn("Quote guard test", prompt)
        self.assertIn("Do not invent quotes", prompt)
        self.assertIn("Alex Hormozi", profile.content)


if __name__ == "__main__":
    unittest.main()
