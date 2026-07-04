from __future__ import annotations

import json

from fastapi import HTTPException

from memory_builder.advisor_seeds import default_source_config
from memory_builder.config import load_persona_config, save_persona_config
from memory_builder.models import PersonaConfig
from memory_builder.paths import persona_config_path, project_root

from api.schemas import PersonaSummary

PERSONAS_DIR = project_root() / "memory_builder" / "config" / "personas"
ADVISOR_CONFIG_PATH = project_root() / "advisors" / "persona_config.json"


def _load_advisor_names() -> dict[str, str]:
    if not ADVISOR_CONFIG_PATH.exists():
        return {}
    data = json.loads(ADVISOR_CONFIG_PATH.read_text(encoding="utf-8"))
    advisors = data.get("advisors", {})
    return {
        advisor_id.strip().lower(): str(info.get("name", advisor_id))
        for advisor_id, info in advisors.items()
    }


def _source_config_template(persona_id: str, display_name: str) -> dict:
    return default_source_config(persona_id, display_name)


def list_persona_ids() -> list[str]:
    yaml_ids = set()
    if PERSONAS_DIR.is_dir():
        yaml_ids = {path.stem for path in PERSONAS_DIR.glob("*.yaml")}
    advisor_ids = set(_load_advisor_names())
    return sorted(yaml_ids | advisor_ids)


def ensure_persona_ready(persona_id: str) -> str:
    persona_id = persona_id.strip().lower()
    path = persona_config_path(persona_id, project_root())
    if path.exists():
        return persona_id

    display_name = _load_advisor_names().get(persona_id)
    if display_name is None:
        raise HTTPException(status_code=404, detail=f"Unknown persona: {persona_id}")

    save_persona_config(persona_id, _source_config_template(persona_id, display_name))
    return persona_id


def get_persona_config(persona_id: str) -> PersonaConfig:
    ensure_persona_ready(persona_id)
    return load_persona_config(persona_id)


def list_personas() -> list[PersonaSummary]:
    summaries: list[PersonaSummary] = []
    advisor_names = _load_advisor_names()
    for persona_id in list_persona_ids():
        path = persona_config_path(persona_id, project_root())
        if path.exists():
            config = load_persona_config(persona_id)
            display_name = config.display_name
        else:
            display_name = advisor_names.get(persona_id, persona_id)
        summaries.append(PersonaSummary(persona_id=persona_id, display_name=display_name))
    return summaries
