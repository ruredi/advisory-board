from __future__ import annotations

from pathlib import Path

import yaml

from memory_builder.models import PersonaConfig
from memory_builder.paths import persona_config_path, project_root


def load_persona_config(persona_id: str, root: Path | None = None) -> PersonaConfig:
    base = project_root()
    path = persona_config_path(persona_id, base)
    if not path.exists():
        raise FileNotFoundError(f"Persona config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    seed_files = [str(base / rel) if not Path(rel).is_absolute() else rel for rel in data.get("seed_link_files", [])]
    return PersonaConfig(
        persona_id=data["persona_id"],
        display_name=data["display_name"],
        seed_link_files=seed_files,
        watch_feeds=data.get("watch_feeds", []),
        social_profiles=data.get("social_profiles", []),
        allowed_domains=data.get("allowed_domains", []),
        speaker_names=data.get("speaker_names", []),
        min_confidence=data.get("min_confidence", "weak"),
        embedding_model=data.get("embedding_model", "text-embedding-3-small"),
        extraction_model=data.get("extraction_model", "gemini-2.5-flash"),
        transcription_model=data.get("transcription_model", "gemini-2.5-flash"),
        vision_model=data.get("vision_model", "gemini-2.5-flash"),
        vector_store=data.get("vector_store", "qdrant"),
        qdrant_url=data.get("qdrant_url") or None,
        speaker_labeled_transcription=bool(data.get("speaker_labeled_transcription", False)),
        allow_unlabeled_fallback=bool(data.get("allow_unlabeled_fallback", False)),
    )


def save_persona_config(persona_id: str, data: dict, root: Path | None = None) -> Path:
    base = project_root()
    path = persona_config_path(persona_id, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def persona_config_to_dict(config: PersonaConfig) -> dict:
    base = project_root()
    seed_files = []
    for item in config.seed_link_files:
        path = Path(item)
        try:
            seed_files.append(str(path.relative_to(base)))
        except ValueError:
            seed_files.append(str(path))
    return {
        "persona_id": config.persona_id,
        "display_name": config.display_name,
        "seed_link_files": seed_files,
        "watch_feeds": config.watch_feeds,
        "social_profiles": config.social_profiles,
        "allowed_domains": config.allowed_domains,
        "speaker_names": config.speaker_names,
        "min_confidence": config.min_confidence,
        "embedding_model": config.embedding_model,
        "extraction_model": config.extraction_model,
        "transcription_model": config.transcription_model,
        "vision_model": config.vision_model,
        "vector_store": config.vector_store,
        "qdrant_url": config.qdrant_url or "",
        "speaker_labeled_transcription": config.speaker_labeled_transcription,
        "allow_unlabeled_fallback": config.allow_unlabeled_fallback,
    }
