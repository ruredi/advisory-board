from __future__ import annotations

import unittest

from memory_builder.extraction.prompts import EXTRACTION_SYSTEM, EXTRACTION_USER


class ExtractionPromptTests(unittest.TestCase):
    def test_extraction_system_formats_without_key_error(self) -> None:
        formatted = EXTRACTION_SYSTEM.format(display_name="Alex Hormozi")
        self.assertIn("Alex Hormozi", formatted)
        self.assertIn('"content_type"', formatted)

    def test_extraction_user_formats(self) -> None:
        formatted = EXTRACTION_USER.format(
            display_name="Alex Hormozi",
            title="Episode",
            source_url="https://example.com",
            speaker_names="Alex Hormozi",
            text="Sample text",
        )
        self.assertIn("Sample text", formatted)


if __name__ == "__main__":
    unittest.main()
