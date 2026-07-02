from __future__ import annotations

import unittest
from pathlib import Path

from memory_builder.extraction.extractor import _chunk_text

ROOT = Path(__file__).resolve().parents[1]


class ChunkTextTests(unittest.TestCase):
    def test_short_text_single_chunk(self) -> None:
        self.assertEqual(_chunk_text("hello world", max_chars=100), ["hello world"])

    def test_splits_on_paragraph_boundaries(self) -> None:
        text = ("a" * 8000) + "\n\n" + ("b" * 8000)
        chunks = _chunk_text(text, max_chars=10000)
        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(len(chunk) <= 10000 for chunk in chunks))

    def test_splits_single_newline_caption_style(self) -> None:
        lines = [f"line {index}: " + ("word " * 40) for index in range(400)]
        text = "\n".join(lines)
        chunks = _chunk_text(text, max_chars=12000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 12000 for chunk in chunks))
        self.assertEqual("".join(chunk.replace("\n", "") for chunk in chunks), text.replace("\n", ""))

    def test_hormozi_36_minute_transcript_splits(self) -> None:
        fixture = ROOT / "sources/processed/hormozi/11ea02a842cec5c9/document.txt"
        if not fixture.exists():
            self.skipTest("fixture transcript missing")
        text = fixture.read_text(encoding="utf-8")
        chunks = _chunk_text(text, max_chars=12000)
        self.assertGreater(len(chunks), 15)
        self.assertTrue(all(len(chunk) <= 12000 for chunk in chunks))
        rebuilt_lines: list[str] = []
        for chunk in chunks:
            rebuilt_lines.extend(chunk.split("\n"))
        self.assertEqual(rebuilt_lines, text.split("\n"))


if __name__ == "__main__":
    unittest.main()
