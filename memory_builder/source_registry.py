from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from memory_builder.paths import project_root


@dataclass
class SourceCandidate:
    url: str
    platform: str
    confidence: float
    discovery_source: str
    username: str = ""
    signals: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | approved | rejected | manual
    label: str = ""
    archived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceCandidate:
        return cls(
            url=data["url"],
            platform=data["platform"],
            confidence=float(data.get("confidence", 0.0)),
            discovery_source=data.get("discovery_source", "unknown"),
            username=data.get("username", ""),
            signals=list(data.get("signals", [])),
            status=data.get("status", "pending"),
            label=data.get("label", ""),
            archived=bool(data.get("archived", False)),
        )


@dataclass
class ApprovedSources:
    persona_id: str
    reviewed_at: str
    reviewed_by: str
    sources: list[SourceCandidate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
            "sources": [source.to_dict() for source in self.sources],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovedSources:
        return cls(
            persona_id=data["persona_id"],
            reviewed_at=data["reviewed_at"],
            reviewed_by=data.get("reviewed_by", "unknown"),
            sources=[SourceCandidate.from_dict(item) for item in data.get("sources", [])],
        )


def candidates_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "sources" / "candidates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def approved_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "sources" / "approved"
    path.mkdir(parents=True, exist_ok=True)
    return path


def candidates_path(persona_id: str, root: Path | None = None) -> Path:
    return candidates_dir(root) / f"{persona_id}.json"


def approved_path(persona_id: str, root: Path | None = None) -> Path:
    return approved_dir(root) / f"{persona_id}.yaml"


def save_candidates(persona_id: str, candidates: list[SourceCandidate], root: Path | None = None) -> Path:
    path = candidates_path(persona_id, root)
    payload = {
        "persona_id": persona_id,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_candidates(persona_id: str, root: Path | None = None) -> list[SourceCandidate]:
    path = candidates_path(persona_id, root)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SourceCandidate.from_dict(item) for item in payload.get("candidates", [])]


def save_approved(approved: ApprovedSources, root: Path | None = None) -> Path:
    path = approved_path(approved.persona_id, root)
    path.write_text(yaml.safe_dump(approved.to_dict(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_approved(persona_id: str, root: Path | None = None) -> ApprovedSources | None:
    path = approved_path(persona_id, root)
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return None
    return ApprovedSources.from_dict(data)


def is_sources_approved(persona_id: str, root: Path | None = None) -> bool:
    approved = load_approved(persona_id, root)
    if approved is None:
        return False
    return any(not source.archived for source in approved.sources)


def username_from_url(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if not path_parts:
        return ""
    if path_parts[0].lower() in {"in", "user"} and len(path_parts) > 1:
        return path_parts[1].lower()
    if path_parts[0].startswith("@"):
        return path_parts[0][1:].lower()
    if path_parts[0].lower() == "channel" and len(path_parts) > 1:
        return path_parts[1]
    return path_parts[0].lower()


def approved_to_social_profiles(approved: ApprovedSources) -> list[dict[str, str | int]]:
    from memory_builder.fetch.scrapfly_facebook import facebook_profile_kind

    scraper_platforms = {"x", "twitter", "instagram", "tiktok", "threads", "facebook"}
    social_platforms = scraper_platforms | {"linkedin"}
    profiles: list[dict[str, str | int]] = []
    for source in approved.sources:
        if source.archived:
            continue
        platform = source.platform.lower()
        if platform == "twitter":
            platform = "x"
        if platform not in social_platforms:
            continue
        username = source.username or username_from_url(source.url)
        profile: dict[str, str | int] = {
            "platform": platform,
            "username": username,
            "url": source.url,
            "max_posts": 50,
        }
        if platform == "facebook":
            profile["facebook_kind"] = facebook_profile_kind(source.url)
        profiles.append(profile)
    return profiles


def approved_scraper_profiles(approved: ApprovedSources) -> list[dict[str, str | int]]:
    scraper_platforms = {"x", "twitter", "instagram", "tiktok", "threads", "facebook"}
    profiles = approved_to_social_profiles(approved)
    has_instagram = any(profile["platform"] == "instagram" for profile in profiles)
    selected: list[dict[str, str | int]] = []
    for profile in profiles:
        platform = profile["platform"]
        if platform == "facebook" and has_instagram:
            continue
        if platform in scraper_platforms:
            selected.append(profile)
    return selected
