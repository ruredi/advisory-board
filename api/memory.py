from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException, Query

from api.deps import persona_store
from api.schemas import KnowledgeUnitItem, SearchHit, SearchRequest, SearchResponse, UnitStats
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
    duplicates_only: bool = False,
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
        if duplicates_only:
            query += " AND k.duplicate_of IS NOT NULL"
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
    return [
        KnowledgeUnitItem(
            id=int(row["id"]),
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
        )
        for row in rows
    ]


@router.post("/personas/{persona_id}/search", response_model=SearchResponse)
def search_memory(persona_id: str, body: SearchRequest) -> SearchResponse:
    try:
        search = MemorySearch(persona_id, top_k=body.top_k)
        hits = search.search(body.query)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    response_hits = [
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
        )
        for hit in hits
    ]
    context_pack = build_context_pack(persona_id, body.query, top_k=body.top_k) if body.context_pack else None
    return SearchResponse(hits=response_hits, context_pack=context_pack)
