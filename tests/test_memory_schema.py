from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.config import load_persona_config
from memory_builder.dedup.knowledge_dedup import content_similarity, mark_duplicate_units
from memory_builder.discovery.seed_links import classify_source_type, discover_seed_sources, is_processable_source, parse_seed_link_file
from memory_builder.extraction.extractor import extract_knowledge_units
from memory_builder.models import KnowledgeUnit, SourceRecord, SourceStatus
from memory_builder.retrieval.context_pack import build_context_pack
from memory_builder.storage.sqlite_store import SQLiteStore, content_fingerprint, normalize_url
from memory_builder.storage.vector_index import VectorIndex


class MemorySchemaTests(unittest.TestCase):
    def test_initialize_and_insert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SQLiteStore("hormozi", root)
            store.initialize()
            source_id = store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://example.com/a",
                    source_title="Example",
                    source_type="web",
                    status=SourceStatus.PENDING,
                    source_nature="written",
                )
            )
            unit = KnowledgeUnit(
                persona_id="hormozi",
                source_id=source_id,
                content_type="framework",
                chunk_text="Value Equation overview",
                frameworks=["Value Equation"],
                steps=["dream outcome", "likelihood", "time delay", "effort"],
            )
            unit_id = store.insert_knowledge_unit(unit)
            self.assertGreater(unit_id, 0)
            row = store.get_source_by_url("https://example.com/a")
            self.assertIsNotNone(row)


class DiscoveryTests(unittest.TestCase):
    def test_parse_seed_links(self) -> None:
        seed_file = ROOT / "docs/notebooklm-forrasok/alex-hormozi/alex-hormozi-linkek.txt"
        urls = parse_seed_link_file(seed_file)
        self.assertGreater(len(urls), 20)
        self.assertEqual(classify_source_type("https://www.youtube.com/watch?v=abc"), "youtube")

    def test_discover_seed_sources_filters_profiles(self) -> None:
        records = discover_seed_sources("hormozi", [str(ROOT / "docs/notebooklm-forrasok/alex-hormozi/alex-hormozi-linkek.txt")])
        urls = {record.source_url for record in records}
        self.assertTrue(any("watch?v=" in url or "/shorts/" in url for url in urls))
        self.assertFalse(any(url.endswith("instagram.com/hormozi") for url in urls))


class DedupTests(unittest.TestCase):
    def test_duplicate_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteStore("hormozi", Path(tmp))
            store.initialize()
            source_id = store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://example.com/a",
                    source_title="Example",
                    source_type="web",
                    status=SourceStatus.PENDING,
                    source_nature="written",
                )
            )
            unit = KnowledgeUnit(persona_id="hormozi", source_id=source_id, content_type="framework", chunk_text="Same text")
            first_id = store.insert_knowledge_unit(unit)
            duplicate = KnowledgeUnit(persona_id="hormozi", source_id=source_id, content_type="framework", chunk_text="Same text")
            marked, counts = mark_duplicate_units(store, [duplicate])
            self.assertEqual(counts["duplicate"], 1)
            self.assertFalse(marked[0].is_new_information)
            self.assertEqual(marked[0].duplicate_of, first_id)

    def test_content_similarity(self) -> None:
        score = content_similarity("fix the offer before scaling ads", "fix the offer before you scale ads")
        self.assertGreater(score, 0.5)


class ExtractionTests(unittest.TestCase):
    def test_heuristic_extraction(self) -> None:
        fixture = json.loads((ROOT / "tests/fixtures/hormozi_sample.json").read_text(encoding="utf-8"))
        units = extract_knowledge_units(
            persona_id="hormozi",
            source_id=1,
            display_name="Alex Hormozi",
            speaker_names=["Alex Hormozi"],
            title=fixture["title"],
            source_url=fixture["source_url"],
            text=fixture["text"],
            source_nature=fixture["source_nature"],
        )
        self.assertGreaterEqual(len(units), 2)
        self.assertTrue(any("Value Equation" in unit.frameworks for unit in units))
        self.assertTrue(any(unit.content_type == "quote" for unit in units))


class RetrievalTests(unittest.TestCase):
    def test_search_and_context_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SQLiteStore("hormozi", root)
            store.initialize()
            source_id = store.upsert_source(
                SourceRecord(
                    persona_id="hormozi",
                    source_url="https://example.com/a",
                    source_title="Offer diagnosis",
                    source_type="web",
                    status=SourceStatus.INDEXED,
                    source_nature="written",
                )
            )
            unit = KnowledgeUnit(
                persona_id="hormozi",
                source_id=source_id,
                content_type="framework",
                chunk_text="Weak offers fail because perceived value is too low.",
                frameworks=["Value Equation"],
                steps=["dream outcome", "likelihood", "time delay", "effort"],
            )
            unit_id = store.insert_knowledge_unit(unit)
            VectorIndex(store, root=root).index_unit(unit_id, unit.embedding_text())
            pack = build_context_pack("hormozi", "How does Hormozi diagnose a weak offer?", root=root)
            self.assertIn("Value Equation", pack)
            self.assertIn("Quote guard", pack)


class UtilityTests(unittest.TestCase):
    def test_normalize_url(self) -> None:
        self.assertEqual(
            normalize_url("https://www.youtube.com/watch?v=abc123&utm_source=x"),
            "https://youtube.com/watch?v=abc123",
        )

    def test_persona_config_loads(self) -> None:
        config = load_persona_config("hormozi", ROOT)
        self.assertEqual(config.persona_id, "hormozi")
        self.assertTrue(config.seed_link_files)


if __name__ == "__main__":
    unittest.main()
