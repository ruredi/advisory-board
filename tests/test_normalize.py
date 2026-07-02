from __future__ import annotations

import unittest

from memory_builder.dedup.knowledge_dedup import _framework_overlap
from memory_builder.models import KnowledgeUnit
from memory_builder.normalize import normalize_string_list


class NormalizeStringListTests(unittest.TestCase):
    def test_plain_strings(self) -> None:
        self.assertEqual(normalize_string_list(["A", "B"]), ["A", "B"])

    def test_dict_items(self) -> None:
        self.assertEqual(
            normalize_string_list([{"name": "Value Equation"}, {"title": "Offer"}]),
            ["Value Equation", "Offer"],
        )

    def test_framework_overlap_with_dicts(self) -> None:
        a = KnowledgeUnit(
            persona_id="hormozi",
            source_id=1,
            content_type="framework",
            chunk_text="a",
            frameworks=[{"name": "Value Equation"}],
        )
        b = KnowledgeUnit(
            persona_id="hormozi",
            source_id=2,
            content_type="framework",
            chunk_text="b",
            frameworks=["Value Equation"],
        )
        self.assertTrue(_framework_overlap(a, b))


if __name__ == "__main__":
    unittest.main()
