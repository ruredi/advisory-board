from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum


class StrEnum(str, Enum):
    pass
from typing import Any


class SourceType(StrEnum):
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    WEB = "web"
    PDF = "pdf"
    SOCIAL = "social"
    IMAGE = "image"
    UNKNOWN = "unknown"


class SourceNature(StrEnum):
    WRITTEN = "written"
    NATURAL_SPOKEN = "natural_spoken"
    PERFORMED_SPOKEN = "performed_spoken"
    WRITTEN_PERFORMED_AS_SPEECH = "written_performed_as_speech"
    VISUAL = "visual"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class ContentType(StrEnum):
    PRINCIPLE = "principle"
    FRAMEWORK = "framework"
    PROCESS = "process"
    STEP_BY_STEP = "step_by_step"
    DIAGNOSTIC_LOGIC = "diagnostic_logic"
    EXAMPLE = "example"
    CASE_STUDY = "case_study"
    QUOTE = "quote"
    STORY = "story"
    WARNING = "warning"
    VISUAL_FRAMEWORK = "visual_framework"
    TABLE = "table"
    DIAGRAM = "diagram"
    TRANSCRIPT_CHUNK = "transcript_chunk"


class SourceStatus(StrEnum):
    PENDING = "pending"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PROCESSING = "processing"
    PROCESSED = "processed"
    EXTRACTING = "extracting"
    INDEXED = "indexed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Confidence(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    INSUFFICIENT = "insufficient_evidence"


from memory_builder.normalize import normalize_string_list


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default if default is not None else []
    return json.loads(value)


@dataclass
class SourceRecord:
    persona_id: str
    source_url: str
    source_title: str = ""
    source_type: str = SourceType.UNKNOWN
    source_date: str | None = None
    discovered_at: str | None = None
    processed_at: str | None = None
    content_hash: str | None = None
    status: str = SourceStatus.PENDING
    speaker: str | None = None
    source_nature: str = SourceNature.UNCERTAIN
    raw_path: str | None = None
    error_message: str | None = None
    channel_url: str | None = None
    normalized_title: str | None = None
    id: int | None = None


@dataclass
class KnowledgeUnit:
    persona_id: str
    source_id: int
    content_type: str
    chunk_text: str
    visual_description: str = ""
    topics: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    advice_contexts: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    quotes: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = Confidence.MEDIUM
    retrieval_priority: int = 50
    is_new_information: bool = True
    duplicate_of: int | None = None
    speaker: str | None = None
    source_nature: str = SourceNature.UNCERTAIN
    evidence_type: str = "source_supported"
    id: int | None = None

    def embedding_text(self) -> str:
        parts = [self.chunk_text, self.visual_description]
        frameworks = normalize_string_list(self.frameworks)
        processes = normalize_string_list(self.processes)
        steps = normalize_string_list(self.steps)
        if frameworks:
            parts.append("frameworks: " + ", ".join(frameworks))
        if processes:
            parts.append("processes: " + ", ".join(processes))
        if steps:
            parts.append("steps: " + " > ".join(steps))
        return "\n".join(part for part in parts if part)

    def to_row(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("topics", "frameworks", "processes", "steps", "concepts", "advice_contexts", "examples", "quotes"):
            data[key] = json_dumps(data[key])
        data.pop("id", None)
        return data


@dataclass
class ProcessedDocument:
    title: str
    text: str
    source_nature: str = SourceNature.UNCERTAIN
    metadata: dict[str, Any] = field(default_factory=dict)
    visual_assets: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PersonaConfig:
    persona_id: str
    display_name: str
    seed_link_files: list[str]
    watch_feeds: list[dict[str, str]] = field(default_factory=list)
    social_profiles: list[dict[str, str | int]] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    speaker_names: list[str] = field(default_factory=list)
    min_confidence: str = Confidence.WEAK
    embedding_model: str = "text-embedding-3-small"
    extraction_model: str = "gemini-2.5-flash"
    transcription_model: str = "gemini-2.5-flash"
    vision_model: str = "gemini-2.5-flash"
    vector_store: str = "qdrant"
    qdrant_url: str | None = None
