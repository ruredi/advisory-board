from __future__ import annotations

import base64
import binascii
import importlib.util
import json
from pathlib import Path
from typing import Literal, NamedTuple

import yaml
from fastapi import APIRouter, HTTPException

from api.schemas import (
    AdvisorConfigFileItem,
    AdvisorConfigFileResponse,
    AdvisorConfigFileUpdateRequest,
    AdvisorPhotoResponse,
    AdvisorPhotoUploadRequest,
    AdvisorSummary,
    SoulDeployRequest,
    SoulResponse,
)
from memory_builder.config import load_persona_config, persona_config_to_dict, save_persona_config
from memory_builder.paths import persona_config_path, project_root

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "advisors" / "persona_config.json"
HERMES_PROFILES = Path.home() / ".hermes" / "profiles"
DASHBOARD_PUBLIC = ROOT / "dashboard" / "public"
ADVISOR_PHOTO_DIR = DASHBOARD_PUBLIC / "advisors"
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif", "avif")


ConfigKind = Literal["json", "yaml", "markdown"]


class ConfigFileDef(NamedTuple):
    key: str
    label: str
    kind: ConfigKind
    shared: bool
    can_create: bool


def _load_render_soul():
    module_path = ROOT / "scripts" / "render_profile_soul.py"
    spec = importlib.util.spec_from_file_location("render_profile_soul", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load render_profile_soul")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_advisor_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _normalize_advisor_id(advisor_id: str) -> str:
    return advisor_id.strip().lower()


def _ensure_advisor(advisor_id: str) -> dict:
    data = _load_advisor_config()
    advisor_id = _normalize_advisor_id(advisor_id)
    advisors = data.get("advisors", {})
    if advisor_id not in advisors:
        raise HTTPException(status_code=404, detail="Advisor not found")
    return advisors[advisor_id]


def _source_config_template(advisor_id: str, display_name: str) -> dict:
    return {
        "persona_id": advisor_id,
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


CONFIG_FILE_DEFS = {
    "structured_persona": ConfigFileDef(
        key="structured_persona",
        label="Strukturált advisor config",
        kind="json",
        shared=True,
        can_create=False,
    ),
    "advisor_lens": ConfigFileDef(
        key="advisor_lens",
        label="Durable advisor lens",
        kind="markdown",
        shared=False,
        can_create=False,
    ),
    "source_config": ConfigFileDef(
        key="source_config",
        label="Forrás és memória pipeline YAML",
        kind="yaml",
        shared=False,
        can_create=True,
    ),
    "approved_profiles": ConfigFileDef(
        key="approved_profiles",
        label="Jóváhagyott social/source profilok",
        kind="yaml",
        shared=False,
        can_create=True,
    ),
    "channel_registry": ConfigFileDef(
        key="channel_registry",
        label="Feldolgozási csatorna registry",
        kind="yaml",
        shared=False,
        can_create=True,
    ),
}


def _config_file_path(advisor_id: str, file_key: str) -> Path:
    match file_key:
        case "structured_persona":
            return CONFIG_PATH
        case "advisor_lens":
            return ROOT / "advisors" / f"{advisor_id}.md"
        case "source_config":
            return persona_config_path(advisor_id, project_root())
        case "approved_profiles":
            return ROOT / "sources" / "approved" / f"{advisor_id}.yaml"
        case "channel_registry":
            return ROOT / "sources" / "channels" / f"{advisor_id}.yaml"
        case _:
            raise HTTPException(status_code=404, detail="Advisor config file not found")


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _config_file_item(advisor_id: str, definition: ConfigFileDef) -> AdvisorConfigFileItem:
    path = _config_file_path(advisor_id, definition.key)
    return AdvisorConfigFileItem(
        key=definition.key,
        label=definition.label,
        path=_relative_path(path),
        kind=definition.kind,
        exists=path.exists(),
        shared=definition.shared,
        can_create=definition.can_create,
    )


def _config_file_payload(item: AdvisorConfigFileItem) -> dict:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return item.dict()


def _empty_config_template(advisor_id: str, file_key: str) -> dict:
    match file_key:
        case "source_config":
            advisor = _ensure_advisor(advisor_id)
            return _source_config_template(advisor_id, advisor["name"])
        case "approved_profiles":
            return {
                "persona_id": advisor_id,
                "reviewed_at": None,
                "reviewed_by": "dashboard",
                "sources": [],
            }
        case "channel_registry":
            return {"persona_id": advisor_id, "channels": []}
        case _:
            raise HTTPException(status_code=400, detail="Config file cannot be created")


def _validate_config_content(kind: ConfigKind, content: str) -> None:
    try:
        if kind == "json":
            json.loads(content)
        elif kind == "yaml":
            yaml.safe_load(content) if content.strip() else None
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {kind} content: {exc}") from exc


def _photo_url(advisor_id: str) -> str | None:
    for extension in PHOTO_EXTENSIONS:
        path = ADVISOR_PHOTO_DIR / f"{advisor_id}.{extension}"
        if path.exists():
            return f"/advisors/{advisor_id}.{extension}?v={int(path.stat().st_mtime)}"
    return None


def _detect_image_extension(content_type: str, filename: str, data: bytes) -> str:
    lower_name = filename.lower()
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "avif"

    allowed_by_type = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "image/avif": "avif",
    }
    if content_type in allowed_by_type:
        return allowed_by_type[content_type]

    for suffix, extension in {
        ".jpg": "jpg",
        ".jpeg": "jpg",
        ".png": "png",
        ".webp": "webp",
        ".gif": "gif",
        ".avif": "avif",
    }.items():
        if lower_name.endswith(suffix):
            return extension

    raise HTTPException(status_code=400, detail="Unsupported image type")


router = APIRouter(tags=["advisors"])


@router.get("/advisors", response_model=list[AdvisorSummary])
def list_advisors() -> list[AdvisorSummary]:
    data = _load_advisor_config()
    advisors = data.get("advisors", {})
    return [
        AdvisorSummary(
            advisor_id=advisor_id,
            name=info["name"],
            role=info["role"],
            photo_url=_photo_url(advisor_id),
        )
        for advisor_id, info in advisors.items()
    ]


@router.get("/advisors/{advisor_id}")
def get_advisor(advisor_id: str) -> dict:
    advisor_id = _normalize_advisor_id(advisor_id)
    config = _ensure_advisor(advisor_id)
    md_path = ROOT / "advisors" / f"{advisor_id}.md"
    return {
        "advisor_id": advisor_id,
        "config": config,
        "global": _load_advisor_config().get("global", {}),
        "markdown": md_path.read_text(encoding="utf-8") if md_path.exists() else "",
        "photo_url": _photo_url(advisor_id),
    }


@router.put("/advisors/{advisor_id}/markdown")
def update_advisor_markdown(advisor_id: str, body: dict) -> dict:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    md_path = ROOT / "advisors" / f"{advisor_id}.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Advisor markdown not found")
    content = str(body.get("markdown", ""))
    md_path.write_text(content, encoding="utf-8")
    return {"saved": str(md_path)}


@router.post("/advisors/{advisor_id}/photo", response_model=AdvisorPhotoResponse)
def upload_photo(advisor_id: str, body: AdvisorPhotoUploadRequest) -> AdvisorPhotoResponse:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    try:
        data = base64.b64decode(body.data_base64, validate=True)
    except binascii.Error as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc

    if not data:
        raise HTTPException(status_code=400, detail="Image file is empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="Image file is too large")

    extension = _detect_image_extension(body.content_type, body.filename, data)
    ADVISOR_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    for old_extension in PHOTO_EXTENSIONS:
        old_path = ADVISOR_PHOTO_DIR / f"{advisor_id}.{old_extension}"
        if old_path.exists():
            old_path.unlink()
    target = ADVISOR_PHOTO_DIR / f"{advisor_id}.{extension}"
    target.write_bytes(data)
    return AdvisorPhotoResponse(advisor_id=advisor_id, photo_url=_photo_url(advisor_id))


@router.get("/advisors/{advisor_id}/config-files", response_model=list[AdvisorConfigFileItem])
def list_config_files(advisor_id: str) -> list[AdvisorConfigFileItem]:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    return [
        _config_file_item(advisor_id, definition)
        for definition in CONFIG_FILE_DEFS.values()
    ]


@router.get("/advisors/{advisor_id}/config-files/{file_key}", response_model=AdvisorConfigFileResponse)
def get_config_file(advisor_id: str, file_key: str) -> AdvisorConfigFileResponse:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    definition = CONFIG_FILE_DEFS.get(file_key)
    if definition is None:
        raise HTTPException(status_code=404, detail="Advisor config file not found")
    item = _config_file_item(advisor_id, definition)
    path = _config_file_path(advisor_id, file_key)
    content = path.read_text(encoding="utf-8") if path.exists() else None
    return AdvisorConfigFileResponse(**_config_file_payload(item), content=content)


@router.put("/advisors/{advisor_id}/config-files/{file_key}", response_model=AdvisorConfigFileResponse)
def put_config_file(
    advisor_id: str,
    file_key: str,
    body: AdvisorConfigFileUpdateRequest,
) -> AdvisorConfigFileResponse:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    definition = CONFIG_FILE_DEFS.get(file_key)
    if definition is None:
        raise HTTPException(status_code=404, detail="Advisor config file not found")
    path = _config_file_path(advisor_id, file_key)
    if not path.exists() and not definition.can_create:
        raise HTTPException(status_code=404, detail="Advisor config file not found")
    _validate_config_content(definition.kind, body.content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    item = _config_file_item(advisor_id, definition)
    return AdvisorConfigFileResponse(**_config_file_payload(item), content=body.content)


@router.post("/advisors/{advisor_id}/config-files/{file_key}", response_model=AdvisorConfigFileResponse)
def create_config_file(advisor_id: str, file_key: str) -> AdvisorConfigFileResponse:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    definition = CONFIG_FILE_DEFS.get(file_key)
    if definition is None:
        raise HTTPException(status_code=404, detail="Advisor config file not found")
    if not definition.can_create:
        raise HTTPException(status_code=400, detail="Config file cannot be created")
    path = _config_file_path(advisor_id, file_key)
    if path.exists():
        raise HTTPException(status_code=409, detail="Advisor config file already exists")
    content = yaml.safe_dump(_empty_config_template(advisor_id, file_key), sort_keys=False, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    item = _config_file_item(advisor_id, definition)
    return AdvisorConfigFileResponse(**_config_file_payload(item), content=content)


@router.get("/advisors/{advisor_id}/source-config")
def get_source_config(advisor_id: str) -> dict:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    path = persona_config_path(advisor_id, project_root())
    if not path.exists():
        raise HTTPException(status_code=404, detail="Advisor source config not found")
    config = load_persona_config(advisor_id)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "advisor_id": advisor_id,
        "config": persona_config_to_dict(config),
        "raw_yaml": yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
    }


@router.put("/advisors/{advisor_id}/source-config")
def put_source_config(advisor_id: str, body: dict) -> dict:
    advisor_id = _normalize_advisor_id(advisor_id)
    _ensure_advisor(advisor_id)
    data = body.get("config") or body
    if data.get("persona_id") and data["persona_id"] != advisor_id:
        raise HTTPException(status_code=400, detail="advisor_id mismatch")
    data["persona_id"] = advisor_id
    path = save_persona_config(advisor_id, data)
    return {"saved": str(path)}


@router.post("/advisors/{advisor_id}/source-config")
def create_source_config(advisor_id: str) -> dict:
    advisor_id = _normalize_advisor_id(advisor_id)
    advisor = _ensure_advisor(advisor_id)
    path = persona_config_path(advisor_id, project_root())
    if path.exists():
        raise HTTPException(status_code=409, detail="Advisor source config already exists")
    saved = save_persona_config(advisor_id, _source_config_template(advisor_id, advisor["name"]))
    return {"created": str(saved)}


@router.get("/advisors/{advisor_id}/soul", response_model=SoulResponse)
def get_soul(advisor_id: str) -> SoulResponse:
    module = _load_render_soul()
    advisor_id = _normalize_advisor_id(advisor_id)
    if advisor_id not in module.DISPLAY_NAMES:
        raise HTTPException(status_code=404, detail="Advisor not found")
    rendered = module.render_soul(advisor_id)
    deployed_path = HERMES_PROFILES / advisor_id / "SOUL.md"
    deployed = deployed_path.read_text(encoding="utf-8") if deployed_path.exists() else None
    return SoulResponse(
        advisor_id=advisor_id,
        rendered=rendered,
        deployed=deployed,
        deployed_exists=deployed_path.exists(),
    )


@router.post("/advisors/{advisor_id}/deploy")
def deploy_soul(advisor_id: str, body: SoulDeployRequest) -> dict:
    module = _load_render_soul()
    advisor_id = _normalize_advisor_id(advisor_id)
    if advisor_id not in module.DISPLAY_NAMES:
        raise HTTPException(status_code=404, detail="Advisor not found")
    content = body.content or module.render_soul(advisor_id)
    profile_dir = HERMES_PROFILES / advisor_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    target = profile_dir / "SOUL.md"
    target.write_text(content, encoding="utf-8")
    return {"deployed": str(target)}
