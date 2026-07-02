from __future__ import annotations

from fastapi import APIRouter

from api.deps import ensure_persona
from api.schemas import ReviewSubmitRequest, SourceCandidateItem
from memory_builder.source_registry import load_approved, load_candidates
from memory_builder.source_review import run_discovery, submit_review

router = APIRouter(tags=["review"])


@router.get("/personas/{persona_id}/candidates", response_model=list[SourceCandidateItem])
def list_candidates(persona_id: str) -> list[SourceCandidateItem]:
    ensure_persona(persona_id)
    candidates = load_candidates(persona_id)
    return [
        SourceCandidateItem(
            index=index,
            url=candidate.url,
            platform=candidate.platform,
            confidence=candidate.confidence,
            discovery_source=candidate.discovery_source,
            username=candidate.username,
            signals=candidate.signals,
            status=candidate.status,
        )
        for index, candidate in enumerate(candidates, start=1)
    ]


@router.post("/personas/{persona_id}/candidates/discover", response_model=list[SourceCandidateItem])
def discover_candidates(persona_id: str) -> list[SourceCandidateItem]:
    ensure_persona(persona_id)
    run_discovery(persona_id)
    return list_candidates(persona_id)


@router.post("/personas/{persona_id}/review")
def submit_source_review(persona_id: str, body: ReviewSubmitRequest) -> dict:
    ensure_persona(persona_id)
    approved = submit_review(
        persona_id,
        rejected_indices=set(body.rejected_indices),
        manual_urls=body.manual_urls,
        reviewed_by=body.reviewed_by,
    )
    return {
        "approved_count": len(approved.sources),
        "reviewed_at": approved.reviewed_at,
        "reviewed_by": approved.reviewed_by,
    }


@router.get("/personas/{persona_id}/approved")
def get_approved(persona_id: str) -> dict:
    ensure_persona(persona_id)
    approved = load_approved(persona_id)
    if approved is None:
        return {"approved": False, "sources": []}
    return {"approved": True, **approved.to_dict()}
