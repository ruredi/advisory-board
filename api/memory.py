from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException, Query

from api.deps import persona_store
from api.schemas import (
    KnowledgeUnitDetail,
    KnowledgeUnitItem,
    QuoteItem,
    SearchHit,
    SearchRequest,
    SearchResponse,
    UnitStats,
)
from memory_builder.models import json_loads
from memory_builder.retrieval.context_pack import MemorySearch, build_context_pack
from memory_builder.telemetry.source_labels import platform_label

router = APIRouter(tags=["memory"])


def _row_platform(row) -> str:
    return platform_label(
        str(row["source_type"]),
        str(row["source_url"]),
        channel_url=str(row["channel_url"]) if row["channel_url"] else "",
    )


def _unit_item_from_row(row) -> KnowledgeUnitItem:
    return KnowledgeUnitItem(
        id=int(row["id"]),
        persona_id=str(row["persona_id"]),
        source_id=int(row["source_id"]),
        content_type=str(row["content_type"]),
        chunk_text=str(row["chunk_text"]),
        confidence=str(row["confidence"]),
        is_new_information=bool(row["is_new_information"]),
        duplicate_of=int(row["duplicate_of"]) if row["duplicate_of"] else None,
        source_title=row["source_title"],
        source_url=row["source_url"],
        source_type=str(row["source_type"] or ""),
        channel_url=row["channel_url"],
        frameworks=json_loads(row["frameworks"]),
        processes=json_loads(row["processes"]),
        steps=json_loads(row["steps"]),
        quotes=json_loads(row["quotes"]),
        evidence_type=str(row["evidence_type"] or "source_supported"),
        retrieval_priority=int(row["retrieval_priority"] or 50),
    )


def _unit_detail_from_row(row) -> KnowledgeUnitDetail:
    item = _unit_item_from_row(row)
    return KnowledgeUnitDetail(
        **item.model_dump(),
        visual_description=str(row["visual_description"] or ""),
        topics=json_loads(row["topics"]),
        concepts=json_loads(row["concepts"]),
        advice_contexts=json_loads(row["advice_contexts"]),
        examples=json_loads(row["examples"]),
        speaker=row["speaker"],
        source_nature=str(row["source_nature"] or ""),
    )


@router.get("/personas/{persona_id}/units/stats", response_model=UnitStats)
def unit_stats(persona_id: str) -> UnitStats:
    with persona_store(persona_id) as store:
        conn = store.connect()
        total = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM knowledge_units WHERE persona_id = ?",
                (persona_id,),
            ).fetchone()["c"]
        )
        indexed_sources = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM sources WHERE persona_id = ? AND status = 'indexed'",
                (persona_id,),
            ).fetchone()["c"]
        )
        sources_with_units = int(
            conn.execute(
                "SELECT COUNT(DISTINCT source_id) AS c FROM knowledge_units WHERE persona_id = ?",
                (persona_id,),
            ).fetchone()["c"]
        )
        duplicates = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM knowledge_units WHERE persona_id = ? AND duplicate_of IS NOT NULL",
                (persona_id,),
            ).fetchone()["c"]
        )
        by_content_type = {
            str(row["content_type"]): int(row["c"])
            for row in conn.execute(
                """
                SELECT content_type, COUNT(*) AS c
                FROM knowledge_units
                WHERE persona_id = ?
                GROUP BY content_type
                ORDER BY c DESC
                """,
                (persona_id,),
            ).fetchall()
        }
        by_confidence = {
            str(row["confidence"]): int(row["c"])
            for row in conn.execute(
                """
                SELECT confidence, COUNT(*) AS c
                FROM knowledge_units
                WHERE persona_id = ?
                GROUP BY confidence
                ORDER BY c DESC
                """,
                (persona_id,),
            ).fetchall()
        }
        platform_rows = conn.execute(
            """
            SELECT s.source_type, s.source_url, s.channel_url
            FROM knowledge_units k
            JOIN sources s ON s.id = k.source_id
            WHERE k.persona_id = ?
            """,
            (persona_id,),
        ).fetchall()
        by_platform: Counter[str] = Counter()
        for row in platform_rows:
            by_platform[_row_platform(row)] += 1
    return UnitStats(
        total=total,
        indexed_sources=indexed_sources,
        sources_with_units=sources_with_units,
        duplicates=duplicates,
        by_content_type=by_content_type,
        by_confidence=by_confidence,
        by_platform=dict(by_platform),
    )


@router.get("/personas/{persona_id}/units", response_model=list[KnowledgeUnitItem])
def list_units(
    persona_id: str,
    content_type: str | None = None,
    confidence: str | None = None,
    platform: str | None = None,
    source_id: int | None = None,
    duplicates_only: bool = False,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[KnowledgeUnitItem]:
    with persona_store(persona_id) as store:
        query = """
            SELECT k.*, s.source_title, s.source_url, s.source_type, s.channel_url
            FROM knowledge_units k
            JOIN sources s ON s.id = k.source_id
            WHERE k.persona_id = ?
        """
        params: list[object] = [persona_id]
        if content_type:
            query += " AND k.content_type = ?"
            params.append(content_type)
        if confidence:
            query += " AND k.confidence = ?"
            params.append(confidence)
        if source_id is not None:
            query += " AND k.source_id = ?"
            params.append(source_id)
        if duplicates_only:
            query += " AND k.duplicate_of IS NOT NULL"
        if q:
            query += " AND (k.chunk_text LIKE ? OR s.source_title LIKE ? OR k.quotes LIKE ?)"
            needle = f"%{q}%"
            params.extend([needle, needle, needle])
        query += " ORDER BY k.id DESC"
        if not platform:
            query += " LIMIT ?"
            params.append(limit)
        rows = store.connect().execute(query, params).fetchall()
        if platform:
            rows = [
                row
                for row in rows
                if _row_platform(row).lower() == platform.lower()
            ][:limit]
    return [_unit_item_from_row(row) for row in rows]


@router.get("/personas/{persona_id}/units/{unit_id}", response_model=KnowledgeUnitDetail)
def get_unit(persona_id: str, unit_id: int) -> KnowledgeUnitDetail:
    with persona_store(persona_id) as store:
        row = store.connect().execute(
            """
            SELECT k.*, s.source_title, s.source_url, s.source_type, s.channel_url
            FROM knowledge_units k
            JOIN sources s ON s.id = k.source_id
            WHERE k.persona_id = ? AND k.id = ?
            """,
            (persona_id, unit_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Unit not found")
    return _unit_detail_from_row(row)


@router.get("/personas/{persona_id}/quotes", response_model=list[QuoteItem])
def list_quotes(
    persona_id: str,
    source_id: int | None = None,
    speaker: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[QuoteItem]:
    with persona_store(persona_id) as store:
        query = """
            SELECT k.id, k.source_id, k.content_type, k.confidence, k.quotes,
                   s.source_title, s.source_url
            FROM knowledge_units k
            JOIN sources s ON s.id = k.source_id
            WHERE k.persona_id = ?
              AND k.quotes IS NOT NULL
              AND k.quotes != '[]'
        """
        params: list[object] = [persona_id]
        if source_id is not None:
            query += " AND k.source_id = ?"
            params.append(source_id)
        query += " ORDER BY k.id DESC LIMIT ?"
        params.append(limit)
        rows = store.connect().execute(query, params).fetchall()

    items: list[QuoteItem] = []
    speaker_needle = speaker.lower() if speaker else ""
    text_needle = q.lower() if q else ""
    for row in rows:
        quotes = json_loads(row["quotes"])
        if not isinstance(quotes, list):
            continue
        for quote in quotes:
            if not isinstance(quote, dict):
                continue
            text = str(quote.get("text", "")).strip()
            if not text:
                continue
            quote_speaker = str(quote.get("speaker", "") or "")
            if speaker_needle and speaker_needle not in quote_speaker.lower():
                continue
            if text_needle and text_needle not in text.lower():
                continue
            items.append(
                QuoteItem(
                    unit_id=int(row["id"]),
                    source_id=int(row["source_id"]),
                    text=text,
                    speaker=quote_speaker or None,
                    source_title=row["source_title"],
                    source_url=str(quote.get("source_url") or row["source_url"]),
                    source_link=str(quote.get("source_link") or quote.get("source_url") or row["source_url"]),
                    segment_id=str(quote.get("segment_id") or "") or None,
                    start_seconds=_optional_float(quote.get("start_seconds")),
                    end_seconds=_optional_float(quote.get("end_seconds")),
                    is_verbatim=bool(quote.get("is_verbatim", True)),
                    content_type=str(row["content_type"]),
                    confidence=str(row["confidence"]),
                )
            )
            if len(items) >= limit:
                return items
    return items


@router.post("/personas/{persona_id}/search", response_model=SearchResponse)
def search_memory(persona_id: str, body: SearchRequest) -> SearchResponse:
    try:
        search = MemorySearch(persona_id, top_k=body.top_k)
        hits = search.search(body.query)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    unit_ids = [hit.unit_id for hit in hits]
    row_by_id: dict[int, object] = {}
    if unit_ids:
        with persona_store(persona_id) as store:
            placeholders = ",".join("?" for _ in unit_ids)
            rows = store.connect().execute(
                f"""
                SELECT k.id, k.is_new_information, k.retrieval_priority, k.quotes
                FROM knowledge_units k
                WHERE k.id IN ({placeholders})
                """,
                unit_ids,
            ).fetchall()
            row_by_id = {int(row["id"]): row for row in rows}

    response_hits = []
    for hit in hits:
        extra = row_by_id.get(hit.unit_id)
        response_hits.append(
            SearchHit(
                unit_id=hit.unit_id,
                score=hit.score,
                chunk_text=hit.chunk_text,
                content_type=hit.content_type,
                confidence=hit.confidence,
                source_title=hit.source_title,
                source_url=hit.source_url,
                source_date=hit.source_date,
                source_type=hit.source_type,
                channel_url=hit.channel_url,
                evidence_type=hit.evidence_type,
                frameworks=hit.frameworks,
                processes=hit.processes,
                steps=hit.steps,
                quotes=hit.quotes,
                retrieval_priority=int(extra["retrieval_priority"]) if extra else 50,
                is_new_information=bool(extra["is_new_information"]) if extra else True,
            )
        )
    context_pack = build_context_pack(persona_id, body.query, top_k=body.top_k) if body.context_pack else None
    return SearchResponse(hits=response_hits, context_pack=context_pack)


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
