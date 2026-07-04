from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memory_builder.models import SourceRecord
    from memory_builder.storage.sqlite_store import SQLiteStore


def is_newer_than(published_iso: str | None, watermark_iso: str | None) -> bool:
    if watermark_iso is None:
        return True
    if published_iso is None:
        return True
    return published_iso > watermark_iso


def parse_http_last_modified(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def parse_twitter_created_at(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def parse_unix_timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp <= 0:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def resolve_watermark(*candidates: str | None) -> str | None:
    dates = [candidate for candidate in candidates if candidate]
    return max(dates) if dates else None


def bootstrap_channel_watermark(
    store: SQLiteStore | None,
    channel_url: str,
    registry_watermark: str | None,
) -> str | None:
    db_watermark = store.max_source_date_for_channel(channel_url) if store else None
    return resolve_watermark(registry_watermark, db_watermark)


def bootstrap_profile_watermark(
    store: SQLiteStore | None,
    profile_url: str,
    registry_watermark: str | None = None,
    *,
    platform: str | None = None,
) -> str | None:
    db_watermark = store.max_source_date_for_channel(profile_url) if store else None
    if db_watermark is None and store and platform:
        db_watermark = store.max_source_date_for_platform(platform)
    return resolve_watermark(registry_watermark, db_watermark)


def bootstrap_profile_floor_watermark(
    store: SQLiteStore | None,
    profile_url: str,
    *,
    platform: str | None = None,
) -> str | None:
    db_floor = store.min_source_date_for_channel(profile_url) if store else None
    if db_floor is None and store and platform:
        db_floor = store.min_source_date_for_platform(platform)
    return db_floor


def filter_new_source_records(
    store: SQLiteStore | None,
    records: list[SourceRecord],
) -> list[SourceRecord]:
    if store is None:
        return records
    new_records: list[SourceRecord] = []
    for record in records:
        if store.source_url_is_new(record.source_url):
            new_records.append(record)
    return new_records
