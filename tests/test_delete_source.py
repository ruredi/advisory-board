from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_builder.models import KnowledgeUnit, SourceRecord, SourceStatus
from memory_builder.storage.sqlite_store import SQLiteStore


class DeleteSourceTests(unittest.TestCase):
    def test_delete_source_cascades_knowledge_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SQLiteStore("hormozi", root)
            store.initialize()
            source_id = store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://example.com/video",
                    source_title="Example",
                    source_type="web",
                    status=SourceStatus.INDEXED,
                )
            )
            unit_id = store.insert_knowledge_unit(
                KnowledgeUnit(
                    persona_id="hormozi",
                    source_id=source_id,
                    content_type="quote",
                    chunk_text="hello",
                )
            )
            deleted_units = store.delete_source(source_id)
            self.assertEqual(deleted_units, [unit_id])
            self.assertIsNone(store.get_source_by_id(source_id))
            remaining = store.connect().execute(
                "SELECT COUNT(*) AS c FROM knowledge_units WHERE source_id = ?",
                (source_id,),
            ).fetchone()["c"]
            self.assertEqual(int(remaining), 0)


if __name__ == "__main__":
    unittest.main()
