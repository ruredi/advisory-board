from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from memory_builder.processors.diarized_transcript import TranscriptSegment, TranscriptSegments
from memory_builder.storage.qdrant_store import QdrantStore
from memory_builder.storage.segment_index import SegmentIndex, segment_point_id
from memory_builder.storage.vector_index import VectorIndex


class SegmentIndexTests(unittest.TestCase):
    def test_segment_point_ids_are_stable_uuid_strings(self) -> None:
        first = segment_point_id(7433, 0)
        second = segment_point_id(7433, 1)
        again = segment_point_id(7433, 0)
        self.assertEqual(first, again)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 36)
        self.assertGreater(first.count("-"), 0)

    @patch("memory_builder.storage.embeddings.EmbeddingClient.embed")
    def test_index_and_search_segments(self, mock_embed) -> None:
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.2, 0.1, 0.0]]
        store = MagicMock()
        store.persona_id = "hormozi"
        store.root = None
        vector_index = VectorIndex(store, qdrant_url=None)
        vector_index.qdrant = QdrantStore.memory_client()
        segment_index = SegmentIndex(vector_index)

        segments = TranscriptSegments(
            display_name="Alex Hormozi",
            transcription_mode="text_attributed",
            segments=[
                TranscriptSegment(
                    segment_id="seg-1",
                    speaker="Alex Hormozi",
                    speaker_type="target",
                    text="Raise prices when demand exceeds capacity.",
                ),
                TranscriptSegment(
                    segment_id="seg-2",
                    speaker="Speaker 1",
                    speaker_type="other",
                    text="Can you repeat that?",
                ),
            ],
        )
        indexed = segment_index.index_source_segments(
            source_id=7,
            segments=segments,
            source_url="https://example.com/reel",
            source_title="Reel",
        )
        self.assertEqual(indexed, 2)

        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        hits = segment_index.search("pricing capacity", top_k=2)
        self.assertTrue(hits)
        self.assertEqual(hits[0].speaker_type, "target")
        self.assertEqual(hits[0].segment_id, "seg-1")

        unit_hits = vector_index.search("pricing capacity", top_k=2)
        self.assertEqual(unit_hits, [])


if __name__ == "__main__":
    unittest.main()
