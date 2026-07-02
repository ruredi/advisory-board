from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_builder.dedup.source_dedup import SourceChangeKind, classify_source_change
from memory_builder.extraction.visual_units import visual_assets_to_units
from memory_builder.models import KnowledgeUnit, SourceRecord, SourceStatus
from memory_builder.retrieval.context_pack import MemorySearch
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.storage.vector_index import VectorIndex


GOLDEN_QUERIES = json.loads((ROOT / "tests/fixtures/golden_queries_hormozi.json").read_text(encoding="utf-8"))


def seed_hormozi_memory(root: Path) -> SQLiteStore:
    store = SQLiteStore("hormozi", root)
    store.initialize()
    source_id = store.upsert_source(
        SourceRecord(
            persona_id="hormozi",
            source_url="https://example.com/offer-teaching",
            source_title="Offer diagnosis teaching",
            source_type="web",
            status=SourceStatus.INDEXED,
            source_nature="natural_spoken",
        )
    )
    units = [
        KnowledgeUnit(
            persona_id="hormozi",
            source_id=source_id,
            content_type="framework",
            chunk_text="Most businesses do not have a traffic problem first. They have an offer problem.",
            frameworks=["Value Equation"],
            steps=["dream outcome", "perceived likelihood of achievement", "time delay", "effort and sacrifice"],
        ),
        KnowledgeUnit(
            persona_id="hormozi",
            source_id=source_id,
            content_type="diagnostic_logic",
            chunk_text="To diagnose a weak offer, check whether perceived value is too low before scaling ads.",
            advice_contexts=["weak offer diagnosis"],
        ),
        KnowledgeUnit(
            persona_id="hormozi",
            source_id=source_id,
            content_type="step_by_step",
            chunk_text="Increase perceived value by improving proof, reducing time delay, and lowering effort.",
            processes=["increase perceived value"],
            steps=["improve proof", "reduce time delay", "lower effort"],
        ),
        KnowledgeUnit(
            persona_id="hormozi",
            source_id=source_id,
            content_type="warning",
            chunk_text="Raise prices only after the offer is strong enough that conversion remains healthy.",
            advice_contexts=["when to raise prices"],
        ),
        KnowledgeUnit(
            persona_id="hormozi",
            source_id=source_id,
            content_type="diagnostic_logic",
            chunk_text="Poor conversion often means the offer is unclear, weak, or untrusted rather than a traffic issue.",
            advice_contexts=["poor conversion diagnosis"],
        ),
    ]
    index = VectorIndex(store, root=root)
    for unit in units:
        unit_id = store.insert_knowledge_unit(unit)
        index.index_unit(unit_id, unit.embedding_text())
    return store


class SourceChangeTests(unittest.TestCase):
    def test_classify_source_change(self) -> None:
        self.assertEqual(
            classify_source_change(existing_status="pending", existing_content_hash=None, new_content_hash="abc"),
            SourceChangeKind.NEW,
        )
        self.assertEqual(
            classify_source_change(existing_status="indexed", existing_content_hash="abc", new_content_hash="abc"),
            SourceChangeKind.UNCHANGED,
        )
        self.assertEqual(
            classify_source_change(existing_status="indexed", existing_content_hash="abc", new_content_hash="def"),
            SourceChangeKind.UPDATED,
        )


class VisualUnitTests(unittest.TestCase):
    def test_visual_assets_to_units(self) -> None:
        units = visual_assets_to_units(
            persona_id="hormozi",
            source_id=1,
            source_url="https://example.com/pdf",
            visual_assets=[
                {
                    "path": "/tmp/chart.png",
                    "description": "Value Equation framework diagram.\n1. Dream outcome\n2. Perceived likelihood",
                    "page": 3,
                }
            ],
        )
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].content_type, "step_by_step")
        self.assertIn("Value Equation", units[0].frameworks)
        self.assertGreaterEqual(len(units[0].steps), 2)


class GoldenRetrievalTests(unittest.TestCase):
    def test_golden_queries_return_relevant_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_hormozi_memory(root)
            search = MemorySearch("hormozi", root=root, top_k=3)
            for case in GOLDEN_QUERIES:
                hits = search.search(case["query"])
                self.assertGreater(len(hits), 0, msg=f"No hits for query: {case['query']}")
                combined = " ".join(hit.chunk_text.lower() for hit in hits)
                combined += " ".join(step.lower() for hit in hits for step in hit.steps)
                combined += " ".join(framework.lower() for hit in hits for framework in hit.frameworks)
                self.assertTrue(
                    any(token in combined for token in case["expect_any"]),
                    msg=f"Query '{case['query']}' missed expected tokens in: {combined[:300]}",
                )


if __name__ == "__main__":
    unittest.main()
