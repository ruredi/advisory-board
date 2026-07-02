from __future__ import annotations

from memory_builder.config import load_persona_config
from memory_builder.models import PersonaConfig
from memory_builder.paths import project_root

from api.schemas import PersonaSummary

PERSONAS_DIR = project_root() / "memory_builder" / "config" / "personas"


def list_persona_ids() -> list[str]:
    if not PERSONAS_DIR.is_dir():
        return []
    return sorted(path.stem for path in PERSONAS_DIR.glob("*.yaml"))


def get_persona_config(persona_id: str) -> PersonaConfig:
    return load_persona_config(persona_id)


def list_personas() -> list[PersonaSummary]:
    summaries: list[PersonaSummary] = []
    for persona_id in list_persona_ids():
        config = load_persona_config(persona_id)
        summaries.append(
            PersonaSummary(persona_id=config.persona_id, display_name=config.display_name)
        )
    return summaries
