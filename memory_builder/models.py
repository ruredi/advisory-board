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


class MediaFormat(StrEnum):
    """Primary media modality of a source (text < image < video < audio priority)."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    UNKNOWN = "unknown"


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

MAX_EMBEDDING_METADATA_ITEMS = 12


def build_embedding_text(
    *,
    chunk_text: str,
    visual_description: str = "",
    frameworks: Any = None,
    processes: Any = None,
    steps: Any = None,
) -> str:
    parts = [chunk_text, visual_description]
    normalized_frameworks = normalize_string_list(frameworks)[:MAX_EMBEDDING_METADATA_ITEMS]
    normalized_processes = normalize_string_list(processes)[:MAX_EMBEDDING_METADATA_ITEMS]
    normalized_steps = normalize_string_list(steps)[:MAX_EMBEDDING_METADATA_ITEMS]
    if normalized_frameworks:
        parts.append("frameworks: " + ", ".join(normalized_frameworks))
    if normalized_processes:
        parts.append("processes: " + ", ".join(normalized_processes))
    if normalized_steps:
        parts.append("steps: " + " > ".join(normalized_steps))
    return "\n".join(part for part in parts if part)


def build_embedding_text_from_row(row: Any) -> str:
    return build_embedding_text(
        chunk_text=row["chunk_text"] or "",
        visual_description=row["visual_description"] or "",
        frameworks=json_loads(row["frameworks"]),
        processes=json_loads(row["processes"]),
        steps=json_loads(row["steps"]),
    )


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
    media_format: str = MediaFormat.UNKNOWN
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
        return build_embedding_text(
            chunk_text=self.chunk_text,
            visual_description=self.visual_description,
            frameworks=self.frameworks,
            processes=self.processes,
            steps=self.steps,
        )

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
    media_format: str = MediaFormat.UNKNOWN
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
    speaker_labeled_transcription: bool = False
    allow_unlabeled_fallback: bool = False
