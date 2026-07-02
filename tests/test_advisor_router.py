import importlib.util
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = ROOT / "scripts" / "advisor.py"


def load_router():
    spec = importlib.util.spec_from_file_location("advisor", ROUTER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdvisorRouterTests(unittest.TestCase):
    def test_parse_slash_command_routes_to_one_advisor(self):
        router = load_router()

        route = router.parse_route("/jobs Should we ship individual chats first?")

        self.assertEqual(route.advisors, ["jobs"])
        self.assertEqual(route.question, "Should we ship individual chats first?")

    def test_parse_colon_command_routes_to_one_advisor(self):
        router = load_router()

        route = router.parse_route("buffett: Is this capital efficient?")

        self.assertEqual(route.advisors, ["buffett"])
        self.assertEqual(route.question, "Is this capital efficient?")

    def test_parse_multi_advisor_colon_command(self):
        router = load_router()

        route = router.parse_route("jobs,buffett: Should we add board mode now?")

        self.assertEqual(route.advisors, ["jobs", "buffett"])
        self.assertEqual(route.question, "Should we add board mode now?")

    def test_parse_full_name_alias(self):
        router = load_router()

        route = router.parse_route("/steve-jobs What should we cut?")

        self.assertEqual(route.advisors, ["jobs"])
        self.assertEqual(route.question, "What should we cut?")

    def test_parse_rejects_unknown_or_missing_route(self):
        router = load_router()

        with self.assertRaises(SystemExit):
            router.parse_route("/unknown Should this fail?")

        with self.assertRaises(SystemExit):
            router.parse_route("This has no route")

    def test_dry_run_cli_prints_route_and_prompt(self):
        result = subprocess.run(
            ["python3", str(ROUTER_PATH), "/jobs Should we ship it?", "--dry-run"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("Route: jobs", result.stdout)
        self.assertIn("DRY RUN", result.stdout)
        self.assertIn("Steve Jobs", result.stdout)
        self.assertIn("Should we ship it?", result.stdout)


if __name__ == "__main__":
    unittest.main()
