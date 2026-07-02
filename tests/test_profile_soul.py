import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_PATH = ROOT / "scripts" / "render_profile_soul.py"
PERSONA_CONFIG_PATH = ROOT / "advisors" / "persona_config.json"


def load_renderer():
    spec = importlib.util.spec_from_file_location("render_profile_soul", RENDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProfileSoulTests(unittest.TestCase):
    def test_persona_config_has_voice_bible_for_every_advisor(self):
        config = json.loads(PERSONA_CONFIG_PATH.read_text(encoding="utf-8"))
        expected = {"jobs", "buffett", "musk", "hormozi", "thiel", "bezos"}

        self.assertEqual(set(config["advisors"]), expected)
        for advisor_id, persona in config["advisors"].items():
            with self.subTest(advisor=advisor_id):
                self.assertIn("speaking_style", persona)
                self.assertGreaterEqual(len(persona["behavior_rules"]), 5)
                self.assertGreaterEqual(len(persona["voice_bible"]["says"]), 10)
                self.assertGreaterEqual(len(persona["voice_bible"]["does_not_say"]), 5)
                self.assertGreaterEqual(len(persona["failure_modes"]), 4)

    def test_rendered_soul_contains_layered_contract_and_voice_bible(self):
        renderer = load_renderer()

        soul = renderer.render_soul("jobs")

        self.assertIn("## 1. Global Safety and Product Rules", soul)
        self.assertIn("## 3. Structured Persona Config", soul)
        self.assertIn("## 4. Behavior Rules", soul)
        self.assertIn("## 5. Voice Bible", soul)
        self.assertIn("## 8. Durable Advisor Lens", soul)
        self.assertIn("Ez most nem termék, hanem feature-lista", soul)
        self.assertIn("Do not create, edit, install, or suggest installing skills", soul)
        self.assertIn("Do not claim to be", soul)

    def test_render_cli_outputs_distinct_advisor_voice(self):
        result = subprocess.run(
            ["python3", str(RENDER_PATH), "musk"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertIn("# Elon Musk — Advisory Board SOUL", result.stdout)
        self.assertIn("fake assumption", result.stdout)
        self.assertIn("Mi a valódi bottleneck?", result.stdout)


if __name__ == "__main__":
    unittest.main()
