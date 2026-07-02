from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_builder import env as env_module
from memory_builder.env import load_project_env


class ProjectEnvTests(unittest.TestCase):
    def setUp(self) -> None:
        env_module._LOADED = False

    def tearDown(self) -> None:
        env_module._LOADED = False
    def test_loads_local_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SCRAPFLY_KEY=test-local-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                load_project_env(root)
                self.assertEqual(os.environ["SCRAPFLY_KEY"], "test-local-key")

    def test_secret_project_fallback_maps_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "advisory-board"
            root.mkdir()
            secret = Path(tmp) / "secret-project"
            secret.mkdir()
            (secret / ".env").write_text("SCRAPFLY_API_KEY=test-secret-key\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                load_project_env(root)
                self.assertEqual(os.environ["SCRAPFLY_KEY"], "test-secret-key")


if __name__ == "__main__":
    unittest.main()
