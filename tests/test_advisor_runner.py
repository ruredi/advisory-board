import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "ask_advisor.py"
ADVISORS_DIR = ROOT / "advisors"


def load_runner():
    spec = importlib.util.spec_from_file_location("ask_advisor", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdvisorRunnerTests(unittest.TestCase):
    def test_runner_lists_expected_advisors(self):
        runner = load_runner()

        self.assertEqual(
            runner.list_advisors(ROOT),
            ["bezos", "buffett", "hormozi", "jobs", "musk", "thiel"],
        )

    def test_build_prompt_contains_profile_question_and_governance(self):
        runner = load_runner()

        profile = runner.load_profile(ROOT, "jobs")
        prompt = runner.build_prompt(profile, "Should we add three more features?")

        self.assertIn("Steve Jobs", prompt)
        self.assertIn("Should we add three more features?", prompt)
        self.assertIn("must not create, edit, install, or suggest installing skills", prompt)
        self.assertIn("Do not claim to be the real person", prompt)
        self.assertIn("Answer as a stable advisory lens", prompt)

    def test_hermes_command_uses_safe_toolset_and_quiet_query(self):
        runner = load_runner()

        command = runner.build_hermes_command("hello")

        self.assertEqual(command[0:2], ["hermes", "chat"])
        self.assertIn("--toolsets", command)
        self.assertIn("safe", command)
        self.assertIn("--quiet", command)
        query_index = command.index("-q")
        self.assertEqual(command[query_index + 1], "hello")

    def test_all_advisor_profiles_have_required_sections_and_governance(self):
        required_files = {
            "jobs.md",
            "buffett.md",
            "musk.md",
            "hormozi.md",
            "thiel.md",
            "bezos.md",
        }

        self.assertTrue(required_files.issubset({path.name for path in ADVISORS_DIR.glob("*.md")}))

        required_phrases = [
            "## Public Identity",
            "## Advisor Role",
            "## Core Lens",
            "## Optimizes For",
            "## Underweights",
            "## Decision Filters",
            "## Answer Style",
            "## Prohibited Behavior",
            "## Source Policy",
            "## Self-Development Policy",
            "must not create, edit, install, or suggest installing skills",
            "must not rewrite its own prompt",
            "must not become a worker agent",
            "Do not claim to be the real person",
        ]

        for file_name in required_files:
            content = (ADVISORS_DIR / file_name).read_text(encoding="utf-8")
            for phrase in required_phrases:
                self.assertIn(phrase, content, f"{file_name} missing {phrase}")

    def test_dry_run_cli_prints_prompt_without_calling_hermes(self):
        result = subprocess.run(
            ["python3", str(RUNNER_PATH), "jobs", "Should we ship it?", "--dry-run"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("Steve Jobs", result.stdout)
        self.assertIn("Should we ship it?", result.stdout)
        self.assertIn("DRY RUN", result.stdout)
    def test_list_cli_lists_advisors_without_question(self):
        result = subprocess.run(
            ["python3", str(RUNNER_PATH), "--list"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("jobs", result.stdout.splitlines())
        self.assertIn("buffett", result.stdout.splitlines())


if __name__ == "__main__":
    unittest.main()
