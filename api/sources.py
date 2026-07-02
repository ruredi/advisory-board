from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, HTTPException, Query

from api.deps import persona_store
from api.schemas import (
    SourceDetail,
    SourceItem,
    SourcePatchRequest,
    SourcePlatformStat,
    SourceStatsResponse,
)
from memory_builder.models import SourceStatus
from memory_builder.telemetry.source_labels import platform_label

router = APIRouter(tags=["sources"])


def _source_item(row) -> SourceItem:
    source_type = str(row["source_type"])
    source_url = str(row["source_url"])
    channel_url = str(row["channel_url"]) if row["channel_url"] else ""
    return SourceItem(
        id=int(row["id"]),
        source_title=row["source_title"],
        source_url=source_url,
        source_type=source_type,
        source_date=row["source_date"],
        status=str(row["status"]),
        channel_url=row["channel_url"],
        error_message=row["error_message"],
        processed_at=row["processed_at"],
        platform=platform_label(source_type, source_url, channel_url=channel_url),
    )


@router.get("/personas/{persona_id}/sources", response_model=list[SourceItem])
def list_sources(
    persona_id: str,
    status: str | None = None,
    platform: str | None = None,
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
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = store.connect().execute(query, params).fetchall()
    items = [_source_item(row) for row in rows]
    if platform:
        items = [item for item in items if item.platform.lower() == platform.lower()]
    return items


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
    processed_text = None
    from memory_builder.fetch.downloader import source_slug
    from memory_builder.paths import sources_processed_dir

    processed_dir = sources_processed_dir(persona_id) / source_slug(str(row["source_url"]))
    doc = processed_dir / "document.txt"
    if doc.exists():
        processed_text = doc.read_text(encoding="utf-8")[:8000]
    return SourceDetail(
        **item.model_dump(),
        content_hash=row["content_hash"],
        raw_path=row["raw_path"],
        unit_count=int(unit_count),
        processed_text=processed_text,
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
