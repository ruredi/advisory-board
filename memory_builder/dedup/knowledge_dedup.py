from __future__ import annotations

import re
from enum import Enum

from memory_builder.models import ContentType, KnowledgeUnit
from memory_builder.normalize import normalize_string_list
from memory_builder.storage.sqlite_store import content_fingerprint


class InformationKind(str, Enum):
    NEW = "new"
    DUPLICATE = "duplicate"
    REPEATED_IDEA = "repeated_idea"
    NEW_EXAMPLE = "new_example"
    NEW_FRAMEWORK = "new_framework"
    NEW_PROCESS = "new_process"
    NEW_QUOTE = "new_quote"
    CLARIFICATION = "clarification"


SIMILARITY_DUPLICATE_THRESHOLD = 0.92
SIMILARITY_REPEATED_IDEA_THRESHOLD = 0.78


def filter_speaker_content(text: str, speaker_names: list[str]) -> str:
    if not speaker_names:
        return text
    kept: list[str] = []
    for paragraph in re.split(r"\n{2,}", text):
        lowered = paragraph.lower()
        if any(name.lower() in lowered for name in speaker_names):
            kept.append(paragraph)
            continue
        if re.search(r"\b(i think|i believe|what i|when i|you should|the way i)\b", lowered):
            kept.append(paragraph)
    return "\n\n".join(kept) if kept else text


def is_duplicate_source(existing_hash: str | None, new_hash: str) -> bool:
    return bool(existing_hash and existing_hash == new_hash)


def content_similarity(a: str, b: str) -> float:
    tokens_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    tokens_b = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def _framework_overlap(a: KnowledgeUnit, b: KnowledgeUnit) -> bool:
    frameworks_a = normalize_string_list(a.frameworks)
    frameworks_b = normalize_string_list(b.frameworks)
    if not frameworks_a or not frameworks_b:
        return False
    return bool(set(frameworks_a) & set(frameworks_b))


def _is_clarification(candidate: KnowledgeUnit, existing: KnowledgeUnit) -> bool:
    if not _framework_overlap(candidate, existing):
        return False
    if candidate.steps and existing.steps and candidate.steps != existing.steps:
        return True
    if candidate.processes and existing.processes and candidate.processes != existing.processes:
        return True
    if len(candidate.chunk_text) > len(existing.chunk_text) * 1.15:
        return True
    return False


def _information_kind(unit: KnowledgeUnit) -> InformationKind:
    if unit.content_type == ContentType.QUOTE:
        return InformationKind.NEW_QUOTE
    if unit.content_type in {ContentType.FRAMEWORK, ContentType.VISUAL_FRAMEWORK}:
        return InformationKind.NEW_FRAMEWORK
    if unit.content_type in {ContentType.PROCESS, ContentType.STEP_BY_STEP, ContentType.DIAGRAM}:
        return InformationKind.NEW_PROCESS
    if unit.content_type in {ContentType.EXAMPLE, ContentType.CASE_STUDY}:
        return InformationKind.NEW_EXAMPLE
    return InformationKind.NEW


def classify_unit_novelty(store, unit: KnowledgeUnit) -> tuple[InformationKind, int | None]:
    fingerprint = content_fingerprint(unit)
    existing_id = store.find_unit_by_fingerprint(fingerprint)
    if existing_id:
        return InformationKind.DUPLICATE, existing_id

    rows = store.list_knowledge_units()
    best_match_id: int | None = None
    best_score = 0.0
    best_row = None
    for row in rows:
        existing = store.row_to_knowledge_unit(row)
        score = content_similarity(unit.chunk_text, existing.chunk_text)
        if score > best_score:
            best_score = score
            best_match_id = int(row["id"])
            best_row = existing

    if best_row and best_score >= SIMILARITY_DUPLICATE_THRESHOLD:
        return InformationKind.DUPLICATE, best_match_id
    if best_row and best_score >= SIMILARITY_REPEATED_IDEA_THRESHOLD:
        return InformationKind.REPEATED_IDEA, best_match_id
    if best_row and _is_clarification(unit, best_row):
        return InformationKind.CLARIFICATION, best_match_id

    return _information_kind(unit), None


def mark_duplicate_units(store, units: list[KnowledgeUnit]) -> tuple[list[KnowledgeUnit], dict[str, int]]:
    accepted: list[KnowledgeUnit] = []
    counts = {
        "duplicate": 0,
        "repeated_idea": 0,
        "clarification": 0,
        "new": 0,
    }
    for unit in units:
        kind, duplicate_of = classify_unit_novelty(store, unit)
        if kind == InformationKind.DUPLICATE:
            unit.is_new_information = False
            unit.duplicate_of = duplicate_of
            counts["duplicate"] += 1
        elif kind == InformationKind.REPEATED_IDEA:
            unit.is_new_information = False
            unit.duplicate_of = duplicate_of
            counts["repeated_idea"] += 1
        elif kind == InformationKind.CLARIFICATION:
            unit.is_new_information = True
            unit.duplicate_of = None
            unit.retrieval_priority = min(100, unit.retrieval_priority + 15)
            counts["clarification"] += 1
        else:
            unit.is_new_information = True
            unit.duplicate_of = None
            counts["new"] += 1
        accepted.append(unit)
    return accepted, counts
