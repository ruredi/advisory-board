from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from api.deps import ensure_persona
from api.schemas import PersonaSummary
from memory_builder.config import load_persona_config, persona_config_to_dict, save_persona_config
from memory_builder.paths import persona_config_path, project_root

router = APIRouter(tags=["persona-config"])


@router.get("/personas/{persona_id}/config")
def get_config(persona_id: str) -> dict:
    ensure_persona(persona_id)
    config = load_persona_config(persona_id)
    path = persona_config_path(persona_id, project_root())
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"config": persona_config_to_dict(config), "raw_yaml": yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)}


@router.put("/personas/{persona_id}/config")
def put_config(persona_id: str, body: dict) -> dict:
    ensure_persona(persona_id)
    data = body.get("config") or body
    if data.get("persona_id") and data["persona_id"] != persona_id:
        raise HTTPException(status_code=400, detail="persona_id mismatch")
    data["persona_id"] = persona_id
    path = save_persona_config(persona_id, data)
    return {"saved": str(path)}


@router.post("/personas", response_model=PersonaSummary)
def create_persona(body: dict) -> PersonaSummary:
    persona_id = str(body.get("persona_id", "")).strip()
    display_name = str(body.get("display_name", "")).strip()
    if not persona_id or not display_name:
        raise HTTPException(status_code=400, detail="persona_id and display_name required")
    path = persona_config_path(persona_id, project_root())
    if path.exists():
        raise HTTPException(status_code=409, detail="Persona already exists")
    template = {
        "persona_id": persona_id,
        "display_name": display_name,
        "seed_link_files": [],
        "speaker_names": [display_name],
        "allowed_domains": [],
        "watch_feeds": [],
        "social_profiles": [],
        "min_confidence": "weak",
        "embedding_model": "text-embedding-3-small",
        "extraction_model": "gemini-2.5-flash",
        "transcription_model": "gemini-2.5-flash",
        "vision_model": "gemini-2.5-flash",
        "vector_store": "qdrant",
        "qdrant_url": "",
    }
    save_persona_config(persona_id, template)
    return PersonaSummary(persona_id=persona_id, display_name=display_name)
