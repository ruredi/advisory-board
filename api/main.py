from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.advisors import router as advisors_router
from api.channels import router as channels_router
from api.costs import router as costs_router
from api.jobs_router import router as jobs_router
from api.memory import router as memory_router
from api.overview import build_persona_overview
from api.persona_config import router as persona_config_router
from api.personas import list_persona_ids, list_personas
from api.review import router as review_router
from api.run_watchdog import run_watchdog_lifespan
from api.runs import router as runs_router
from api.schemas import PersonaOverview, PersonaSummary
from api.sources import router as sources_router

app = FastAPI(title="Advisory Board Dashboard API", lifespan=run_watchdog_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3100", "http://localhost:3100"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router)
app.include_router(sources_router)
app.include_router(memory_router)
app.include_router(channels_router)
app.include_router(review_router)
app.include_router(costs_router)
app.include_router(persona_config_router)
app.include_router(advisors_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, str | int]:
    return {"status": "ok", "api_version": 2, "route_count": len(app.routes)}


@app.get("/personas", response_model=list[PersonaSummary])
def personas() -> list[PersonaSummary]:
    return list_personas()


@app.get("/personas/{persona_id}/overview", response_model=PersonaOverview)
def persona_overview(persona_id: str) -> PersonaOverview:
    if persona_id not in list_persona_ids():
        raise HTTPException(status_code=404, detail=f"Unknown persona: {persona_id}")
    return build_persona_overview(persona_id)
