from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def memory_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sources_raw_dir(persona_id: str, root: Path | None = None) -> Path:
    path = (root or project_root()) / "sources" / "raw" / persona_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def sources_processed_dir(persona_id: str, root: Path | None = None) -> Path:
    path = (root or project_root()) / "sources" / "processed" / persona_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(persona_id: str, root: Path | None = None) -> Path:
    return memory_dir(root) / f"{persona_id}.sqlite"


def persona_config_path(persona_id: str, root: Path | None = None) -> Path:
    return (root or project_root()) / "memory_builder" / "config" / "personas" / f"{persona_id}.yaml"
