from __future__ import annotations

from collections.abc import Callable

from memory_builder.models import SourceRecord

# Return False to stop iterating (limit reached). Duplicates should still return True.
OnSourceRecord = Callable[[SourceRecord], bool]


def emit_source_record(
    records: list[SourceRecord],
    record: SourceRecord,
    *,
    on_record: OnSourceRecord | None = None,
) -> bool:
    if on_record is not None:
        return on_record(record)
    records.append(record)
    return True
