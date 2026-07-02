from __future__ import annotations

from enum import Enum

from memory_builder.storage.sqlite_store import text_hash


class SourceChangeKind(str, Enum):
    NEW = "new_source"
    DUPLICATE = "duplicate_source"
    UPDATED = "updated_source"
    UNCHANGED = "unchanged_source"


def classify_source_change(
    *,
    existing_status: str | None,
    existing_content_hash: str | None,
    new_content_hash: str,
) -> SourceChangeKind:
    if not existing_status or existing_status == "pending":
        return SourceChangeKind.NEW
    if existing_content_hash == new_content_hash:
        if existing_status in {"indexed", "processed"}:
            return SourceChangeKind.UNCHANGED
        return SourceChangeKind.DUPLICATE
    if existing_status in {"indexed", "processed", "failed"}:
        return SourceChangeKind.UPDATED
    return SourceChangeKind.NEW


def should_skip_source_processing(change: SourceChangeKind) -> bool:
    return change in {SourceChangeKind.DUPLICATE, SourceChangeKind.UNCHANGED}
