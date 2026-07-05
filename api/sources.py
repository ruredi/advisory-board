from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Query

from api.deps import persona_store
from api.jobs import job_manager
from api.schemas import (
    JobItem,
    SourceDetail,
    SourceItem,
    SourceLinkAnalyzeRequest,
    SourceLinkAnalyzeResponse,
    SourceLinkPersonaMatch,
    SourceLinkSubmitPersonaResult,
    SourceLinkSubmitRequest,
    SourceLinkSubmitResponse,
    SourcePatchRequest,
    SourcePlatformStat,
    SourceStatsResponse,
    SourceWithMemoryItem,
    TranscriptSegmentItem,
    TranscriptSegmentsResponse,
    TranscriptTextResponse,
    TranscriptVariantItem,
)
from memory_builder.submissions.link_submit import analyze_submitted_link, submit_submitted_link
from memory_builder.config import load_persona_config
from memory_builder.models import SourceStatus
from memory_builder.paths import project_root
from memory_builder.pipeline.platform_filter import media_format_sql_filter, platform_sql_filter
from memory_builder.processors.transcript_status import (
    TRANSCRIPT_VARIANTS,
    list_transcript_variants,
    load_source_metadata,
    processed_dir_for_source,
    read_transcript_variant,
    transcript_status_for_source,
)
from memory_builder.processors.transcript_storage import load_transcript_segments
from memory_builder.storage.qdrant_store import QdrantStore
from memory_builder.telemetry.source_labels import platform_label

router = APIRouter(tags=["sources"])


def _job_item(record) -> JobItem:
    return JobItem(
        job_id=record.job_id,
        persona_id=record.persona_id,
        command=record.command,
        status=record.status,
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        exit_code=record.exit_code,
        log_tail=record.log_lines[-50:],
    )


@router.post("/sources/analyze", response_model=SourceLinkAnalyzeResponse)
def analyze_source_link(body: SourceLinkAnalyzeRequest) -> SourceLinkAnalyzeResponse:
    try:
        analysis = analyze_submitted_link(body.url, hint_persona_id=body.persona_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    resolved = analysis.resolved
    return SourceLinkAnalyzeResponse(
        url=resolved.url,
        normalized_url=resolved.normalized_url,
        kind=resolved.kind,
        source_type=resolved.source_type,
        platform=resolved.platform,
        title=resolved.title,
        channel_url=resolved.channel_url,
        processable=resolved.processable,
        message=resolved.message,
        matched_personas=[
            SourceLinkPersonaMatch(
                persona_id=item.persona_id,
                display_name=item.display_name,
                confidence=item.confidence,
                signals=item.signals,
                selected=item.selected,
            )
            for item in analysis.matched_personas
        ],
    )


@router.post("/sources/submit", response_model=SourceLinkSubmitResponse)
def submit_source_link(body: SourceLinkSubmitRequest) -> SourceLinkSubmitResponse:
    persona_ids = body.persona_ids
    if not persona_ids and body.persona_id:
        persona_ids = [body.persona_id]
    try:
        result = submit_submitted_link(
            body.url,
            persona_ids=persona_ids,
            process=body.process,
            hint_persona_id=body.persona_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    resolved = result.resolved
    return SourceLinkSubmitResponse(
        url=resolved.url,
        normalized_url=resolved.normalized_url,
        kind=resolved.kind,
        source_type=resolved.source_type,
        platform=resolved.platform,
        title=resolved.title,
        results=[
            SourceLinkSubmitPersonaResult(
                persona_id=item.persona_id,
                source_id=item.source_id,
                channel_id=item.channel_id,
                status=item.status,
                job_id=item.job_id,
                message=item.message,
            )
            for item in result.results
        ],
    )


def _row_media_format(row) -> str:
    try:
        value = row["media_format"]
    except (IndexError, KeyError):
        return "unknown"
    return str(value) if value else "unknown"


def _source_item(row) -> SourceItem:
    source_type = str(row["source_type"])
    source_url = str(row["source_url"])
    channel_url = str(row["channel_url"]) if row["channel_url"] else ""
    return SourceItem(
        id=int(row["id"]),
        persona_id=str(row["persona_id"]),
        source_title=row["source_title"],
        source_url=source_url,
        source_type=source_type,
        source_date=row["source_date"],
        status=str(row["status"]),
        channel_url=row["channel_url"],
        error_message=row["error_message"],
        processed_at=row["processed_at"],
        platform=platform_label(source_type, source_url, channel_url=channel_url),
        media_format=_row_media_format(row),
    )


@router.get("/personas/{persona_id}/sources", response_model=list[SourceItem])
def list_sources(
    persona_id: str,
    status: str | None = None,
    platform: str | None = None,
    media: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[SourceItem]:
    with persona_store(persona_id) as store:
        query = "SELECT * FROM sources WHERE persona_id = ?"
        params: list[object] = [persona_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (source_title LIKE ? OR source_url LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        platform_clause, platform_params = platform_sql_filter(platform)
        query += platform_clause
        params.extend(platform_params)
        media_clause, media_params = media_format_sql_filter(media)
        query += media_clause
        params.extend(media_params)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = store.connect().execute(query, params).fetchall()
    return [_source_item(row) for row in rows]


@router.get("/personas/{persona_id}/sources/stats", response_model=SourceStatsResponse)
def source_stats(persona_id: str) -> SourceStatsResponse:
    with persona_store(persona_id) as store:
        rows = store.connect().execute(
            "SELECT source_type, source_url, channel_url, status FROM sources WHERE persona_id = ?",
            (persona_id,),
        ).fetchall()

    status_counts: Counter[str] = Counter()
    platform_status: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        status = str(row["status"])
        platform = platform_label(
            str(row["source_type"]),
            str(row["source_url"]),
            channel_url=str(row["channel_url"]) if row["channel_url"] else "",
        )
        status_counts[status] += 1
        platform_status[platform][status] += 1

    platforms = sorted(
        (
            SourcePlatformStat(
                platform=platform,
                total=sum(counts.values()),
                status_counts=dict(counts),
            )
            for platform, counts in platform_status.items()
        ),
        key=lambda item: item.total,
        reverse=True,
    )
    return SourceStatsResponse(
        total=len(rows),
        status_counts=dict(status_counts),
        platforms=platforms,
    )


@router.get(
    "/personas/{persona_id}/sources/with-memory",
    response_model=list[SourceWithMemoryItem],
)
def list_sources_with_memory(
    persona_id: str,
    status: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    has_memory: bool | None = None,
    needs_attention: bool = False,
    limit: int = Query(default=200, le=500),
) -> list[SourceWithMemoryItem]:
    with persona_store(persona_id) as store:
        conn = store.connect()
        query = "SELECT * FROM sources WHERE persona_id = ?"
        params: list[object] = [persona_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        if search:
            query += " AND (source_title LIKE ? OR source_url LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        platform_clause, platform_params = platform_sql_filter(platform)
        query += platform_clause
        params.extend(platform_params)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        source_rows = conn.execute(query, params).fetchall()
        source_ids = [int(row["id"]) for row in source_rows]

        unit_rows: list = []
        event_rows: list = []
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            unit_rows = conn.execute(
                f"""
                SELECT id, source_id, content_type, confidence, duplicate_of, chunk_text
                FROM knowledge_units
                WHERE source_id IN ({placeholders})
                ORDER BY id DESC
                """,
                source_ids,
            ).fetchall()
            event_rows = conn.execute(
                f"""
                SELECT pe.source_id, pe.stage, pe.message, pe.created_at
                FROM pipeline_events pe
                JOIN (
                    SELECT source_id, MAX(id) AS max_id
                    FROM pipeline_events
                    WHERE source_id IN ({placeholders})
                    GROUP BY source_id
                ) latest ON latest.source_id = pe.source_id AND latest.max_id = pe.id
                """,
                source_ids,
            ).fetchall()

    memory_by_source: dict[int, dict] = {}
    for row in unit_rows:
        sid = int(row["source_id"])
        bucket = memory_by_source.setdefault(
            sid,
            {
                "unit_count": 0,
                "strong_count": 0,
                "medium_count": 0,
                "weak_count": 0,
                "duplicate_count": 0,
                "content_type_counts": Counter(),
                "latest_unit_preview": None,
            },
        )
        bucket["unit_count"] += 1
        confidence = str(row["confidence"])
        if confidence == "strong":
            bucket["strong_count"] += 1
        elif confidence == "medium":
            bucket["medium_count"] += 1
        elif confidence == "weak":
            bucket["weak_count"] += 1
        if row["duplicate_of"] is not None:
            bucket["duplicate_count"] += 1
        bucket["content_type_counts"][str(row["content_type"])] += 1
        if bucket["latest_unit_preview"] is None:
            bucket["latest_unit_preview"] = str(row["chunk_text"])[:200]

    event_by_source: dict[int, dict] = {
        int(row["source_id"]): {
            "stage": str(row["stage"]),
            "message": str(row["message"]),
            "created_at": str(row["created_at"]),
        }
        for row in event_rows
    }

    items: list[SourceWithMemoryItem] = []
    for row in source_rows:
        base = _source_item(row)
        sid = base.id
        memory = memory_by_source.get(sid)
        event = event_by_source.get(sid)
        unit_count = memory["unit_count"] if memory else 0
        duplicate_count = memory["duplicate_count"] if memory else 0
        weak_count = memory["weak_count"] if memory else 0
        strong_count = memory["strong_count"] if memory else 0
        medium_count = memory["medium_count"] if memory else 0
        needs = (
            base.status == "failed"
            or (base.status == "indexed" and unit_count == 0)
            or (unit_count > 0 and duplicate_count > unit_count / 2)
            or (unit_count > 0 and weak_count > strong_count + medium_count)
        )
        items.append(
            SourceWithMemoryItem(
                **base.model_dump(),
                unit_count=unit_count,
                strong_count=strong_count,
                medium_count=medium_count,
                weak_count=weak_count,
                duplicate_count=duplicate_count,
                content_type_counts=dict(memory["content_type_counts"]) if memory else {},
                latest_unit_preview=memory["latest_unit_preview"] if memory else None,
                latest_event_stage=event["stage"] if event else None,
                latest_event_message=event["message"] if event else None,
                latest_event_at=event["created_at"] if event else None,
                needs_attention=needs,
            )
        )

    if has_memory is not None:
        items = [item for item in items if (item.unit_count > 0) == has_memory]
    if needs_attention:
        items = [item for item in items if item.needs_attention]
    return items


@router.get("/personas/{persona_id}/sources/{source_id}", response_model=SourceDetail)
def get_source(persona_id: str, source_id: int) -> SourceDetail:
    with persona_store(persona_id) as store:
        row = store.connect().execute(
            "SELECT * FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, persona_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
        unit_count = store.connect().execute(
            "SELECT COUNT(*) AS c FROM knowledge_units WHERE source_id = ?",
            (source_id,),
        ).fetchone()["c"]
    item = _source_item(row)
    source_url = str(row["source_url"])
    processed_dir = processed_dir_for_source(persona_id, source_url)
    metadata = load_source_metadata(persona_id, source_url)
    transcript_status = transcript_status_for_source(
        source_type=str(row["source_type"]),
        source_status=str(row["status"]),
        processed_dir=processed_dir,
        metadata=metadata,
    )
    variants = [
        TranscriptVariantItem(**variant)
        for variant in list_transcript_variants(processed_dir)
    ]
    processed_text = read_transcript_variant(processed_dir, "document", limit=8000)
    return SourceDetail(
        **item.model_dump(),
        content_hash=row["content_hash"],
        raw_path=row["raw_path"],
        unit_count=int(unit_count),
        processed_text=processed_text,
        transcript_status=transcript_status,
        transcript_variants=variants,
    )


@router.get(
    "/personas/{persona_id}/sources/{source_id}/transcripts/{variant}",
    response_model=TranscriptTextResponse,
)
def get_source_transcript(persona_id: str, source_id: int, variant: str) -> TranscriptTextResponse:
    with persona_store(persona_id) as store:
        row = store.connect().execute(
            "SELECT source_url FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, persona_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
    processed_dir = processed_dir_for_source(persona_id, str(row["source_url"]))
    text = read_transcript_variant(processed_dir, variant)
    if text is None:
        raise HTTPException(status_code=404, detail=f"Transcript variant not found: {variant}")
    labels = {key: label for key, _filename, label in TRANSCRIPT_VARIANTS}
    return TranscriptTextResponse(
        source_id=source_id,
        variant=variant,
        label=labels.get(variant, variant),
        text=text,
        char_count=len(text),
    )


@router.get(
    "/personas/{persona_id}/sources/{source_id}/segments",
    response_model=TranscriptSegmentsResponse,
)
def get_source_segments(persona_id: str, source_id: int) -> TranscriptSegmentsResponse:
    with persona_store(persona_id) as store:
        row = store.connect().execute(
            "SELECT source_url FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, persona_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
    processed_dir = processed_dir_for_source(persona_id, str(row["source_url"]))
    segments_path = processed_dir / "transcript_segments.json"
    segments = load_transcript_segments(segments_path)
    if segments is None:
        raise HTTPException(status_code=404, detail="No transcript segments for this source")
    return TranscriptSegmentsResponse(
        source_id=source_id,
        display_name=segments.display_name,
        transcription_mode=segments.transcription_mode,
        segments=[
            TranscriptSegmentItem(
                segment_id=segment.segment_id,
                speaker=segment.speaker,
                speaker_type=segment.speaker_type,
                text=segment.text,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                confidence=segment.confidence,
            )
            for segment in segments.segments
        ],
    )


@router.patch("/personas/{persona_id}/sources/{source_id}", response_model=SourceItem)
def patch_source(persona_id: str, source_id: int, body: SourcePatchRequest) -> SourceItem:
    allowed = {
        SourceStatus.PENDING,
        SourceStatus.FAILED,
        SourceStatus.SKIPPED,
        SourceStatus.PROCESSING,
    }
    if body.status and body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported status: {body.status}")
    with persona_store(persona_id) as store:
        row = store.connect().execute(
            "SELECT id FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, persona_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
        if body.status:
            store.update_source_status(source_id, body.status, error_message=None if body.status == SourceStatus.PENDING else None)
        updated = store.connect().execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    return _source_item(updated)


@router.post("/personas/{persona_id}/sources/{source_id}/process", response_model=JobItem)
def process_source(persona_id: str, source_id: int) -> JobItem:
    with persona_store(persona_id) as store:
        if store.get_source_by_id(source_id) is None:
            raise HTTPException(status_code=404, detail="Source not found")
    record = job_manager.start(
        persona_id=persona_id,
        script="memory_sync.py",
        args=[
            "--persona",
            persona_id,
            "--skip-discovery",
            "--source-ids",
            str(source_id),
        ],
    )
    return _job_item(record)


@router.delete("/personas/{persona_id}/sources/{source_id}", status_code=204)
def delete_source(persona_id: str, source_id: int) -> None:
    config = load_persona_config(persona_id)
    root = project_root()
    with persona_store(persona_id) as store:
        try:
            unit_ids = store.delete_source(source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if unit_ids:
        try:
            qdrant = QdrantStore(persona_id, url=config.qdrant_url, root=root)
            qdrant.delete_units(unit_ids)
        except Exception:
            pass
