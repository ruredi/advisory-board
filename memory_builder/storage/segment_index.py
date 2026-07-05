from __future__ import annotations

import uuid
from dataclasses import dataclass

from memory_builder.processors.diarized_transcript import TranscriptSegments
from memory_builder.storage.vector_index import VectorIndex

SEGMENT_POINT_NAMESPACE = uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")


def segment_point_id(source_id: int, segment_index: int) -> str:
    return str(uuid.uuid5(SEGMENT_POINT_NAMESPACE, f"{source_id}:{segment_index}"))


@dataclass
class RetrievedSegment:
    point_id: str
    score: float
    source_id: int
    segment_id: str
    speaker: str
    speaker_type: str
    text: str
    start_seconds: float | None
    end_seconds: float | None
    source_url: str
    source_title: str


class SegmentIndex:
    def __init__(self, vector_index: VectorIndex) -> None:
        self.vector_index = vector_index
        self.qdrant = vector_index.qdrant
        self.embed_client = vector_index.client

    def index_source_segments(
        self,
        *,
        source_id: int,
        segments: TranscriptSegments,
        source_url: str,
        source_title: str,
    ) -> int:
        self.delete_source_segments(source_id)
        if not segments.segments:
            return 0
        texts = [f"{segment.speaker}: {segment.text.strip()}" for segment in segments.segments]
        vectors = self.embed_client.embed(texts)
        indexed = 0
        for index, (segment, vector) in enumerate(zip(segments.segments, vectors, strict=True)):
            point_id = segment_point_id(source_id, index)
            self.qdrant.upsert_segment(
                point_id,
                vector,
                {
                    "source_id": source_id,
                    "segment_id": segment.segment_id,
                    "speaker": segment.speaker,
                    "speaker_type": segment.speaker_type,
                    "text": segment.text,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "confidence": segment.confidence,
                    "source_url": source_url,
                    "source_title": source_title,
                    "transcription_mode": segments.transcription_mode,
                },
            )
            indexed += 1
        return indexed

    def delete_source_segments(self, source_id: int) -> None:
        self.qdrant.delete_segments_for_source(source_id)

    def search(
        self,
        query: str,
        *,
        top_k: int = 6,
        source_id: int | None = None,
    ) -> list[RetrievedSegment]:
        query_vector = self.embed_client.embed([query])[0]
        hits = self.qdrant.search_segments(query_vector, top_k=top_k, source_id=source_id)
        results: list[RetrievedSegment] = []
        for point_id, score, payload in hits:
            results.append(
                RetrievedSegment(
                    point_id=str(point_id),
                    score=score,
                    source_id=int(payload.get("source_id") or 0),
                    segment_id=str(payload.get("segment_id") or ""),
                    speaker=str(payload.get("speaker") or ""),
                    speaker_type=str(payload.get("speaker_type") or "unknown"),
                    text=str(payload.get("text") or ""),
                    start_seconds=_optional_float(payload.get("start_seconds")),
                    end_seconds=_optional_float(payload.get("end_seconds")),
                    source_url=str(payload.get("source_url") or ""),
                    source_title=str(payload.get("source_title") or ""),
                )
            )
        return results


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
