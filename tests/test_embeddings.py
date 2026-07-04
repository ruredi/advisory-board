from __future__ import annotations

import sqlite3
import unittest

from memory_builder.models import KnowledgeUnit, build_embedding_text
from memory_builder.storage.embeddings import MAX_EMBEDDING_INPUT_CHARS, truncate_embedding_input


class EmbeddingTextTests(unittest.TestCase):
    def test_caps_metadata_items_in_embedding_text(self) -> None:
        text = build_embedding_text(
            chunk_text="summary",
            steps=[f"step {index}" for index in range(100)],
        )
        self.assertLess(len(text), 500)
        self.assertIn("step 0", text)
        self.assertNotIn("step 99", text)

    def test_knowledge_unit_embedding_text_stays_bounded(self) -> None:
        unit = KnowledgeUnit(
            persona_id="hormozi",
            source_id=1,
            content_type="step_by_step",
            chunk_text="x" * 2000,
            steps=[f"00:00:{index:02d} caption fragment" for index in range(15_000)],
        )
        self.assertLess(len(unit.embedding_text()), MAX_EMBEDDING_INPUT_CHARS)


class TruncateEmbeddingInputTests(unittest.TestCase):
    def test_short_text_unchanged(self) -> None:
        self.assertEqual(truncate_embedding_input("hello"), "hello")

    def test_long_text_truncated(self) -> None:
        text = "word " * 10_000
        truncated = truncate_embedding_input(text)
        self.assertLessEqual(len(truncated), MAX_EMBEDDING_INPUT_CHARS)


class EmbeddingClientIntegrationTests(unittest.TestCase):
    def test_oversized_db_unit_embeds_after_fix(self) -> None:
        from memory_builder.storage.embeddings import EmbeddingClient

        conn = sqlite3.connect("memory/hormozi.sqlite")
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM knowledge_units WHERE id=3654").fetchone()
        if row is None:
            self.skipTest("fixture unit 3654 not present")
        unit = KnowledgeUnit(
            persona_id=row["persona_id"],
            source_id=row["source_id"],
            content_type=row["content_type"],
            chunk_text=row["chunk_text"],
            visual_description=row["visual_description"],
            steps=__import__("json").loads(row["steps"]),
        )
        client = EmbeddingClient()
        if not client.uses_api:
            self.skipTest("OPENAI_API_KEY not configured")
        vectors = client.embed([unit.embedding_text()])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), client.dimensions)


if __name__ == "__main__":
    unittest.main()
