from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from memory_builder.config import load_persona_config
from memory_builder.dedup.source_dedup import SourceChangeKind, classify_source_change, should_skip_source_processing
from memory_builder.dedup.knowledge_dedup import filter_speaker_content, mark_duplicate_units
from memory_builder.channel_registry import load_channels, save_channels
from memory_builder.dedup.title_dedup import normalize_episode_title, should_skip_podcast_for_youtube_duplicate
from memory_builder.discovery.channel_feeds import discover_channels
from memory_builder.discovery.seed_links import discover_seed_sources
from memory_builder.discovery.social_profiles import discover_social_sources
from memory_builder.extraction.extractor import extract_knowledge_units
from memory_builder.extraction.visual_units import visual_assets_to_units
from memory_builder.models import SourceRecord, SourceStatus, SourceType
from memory_builder.paths import project_root
from memory_builder.pipeline.platform_filter import platform_sql_filter
from memory_builder.processors import process_source
from memory_builder.source_registry import approved_scraper_profiles, load_approved
from memory_builder.storage.sqlite_store import SQLiteStore, text_hash
from memory_builder.storage.vector_index import VectorIndex
from memory_builder.telemetry.context import get_run_context


@dataclass
class PipelineSummary:
    sources_discovered: int = 0
    sources_processed: int = 0
    sources_skipped_unchanged: int = 0
    sources_updated: int = 0
    units_created: int = 0
    units_skipped_duplicate: int = 0
    units_repeated_idea: int = 0
    units_clarification: int = 0
    errors: int = 0


class MemoryPipeline:
    def __init__(
        self,
        persona_id: str,
        root=None,
        *,
        limit: int | None = None,
        dry_run: bool = False,
        only_platform: str | None = None,
        skip_discovery: bool = False,
    ) -> None:
        self.root = root or project_root()
        self.persona_id = persona_id
        self.config = load_persona_config(persona_id, self.root)
        self.store = SQLiteStore(persona_id, self.root)
        self.limit = limit
        self.dry_run = dry_run
        self.only_platform = only_platform
        self.skip_discovery = skip_discovery
        self.summary = PipelineSummary()

    def initialize(self) -> None:
        self.store.initialize()

    def discover(self) -> list[SourceRecord]:
        print("discovery: started", flush=True)
        ctx = get_run_context()
        if ctx:
            ctx.event("discovery", "Source discovery started")
        records = discover_seed_sources(self.persona_id, self.config.seed_link_files)
        registry = load_channels(self.persona_id, self.root)
        channel_records = discover_channels(
            self.persona_id,
            registry,
            store=None if self.dry_run else self.store,
        )
        records.extend(channel_records)
        if not self.dry_run:
            save_channels(registry, self.root)
        approved = load_approved(self.persona_id, self.root)
        if approved:
            social_profiles = approved_scraper_profiles(approved)
        else:
            social_profiles = self.config.social_profiles
        records.extend(
            discover_social_sources(
                self.persona_id,
                social_profiles,
                only_platform=self.only_platform,
            )
        )
        self.summary.sources_discovered = len(records)
        print(f"discovery: found {len(records)} source candidates", flush=True)
        if ctx:
            from collections import Counter

            by_type = Counter(str(record.source_type) for record in records)
            ctx.event(
                "discovery",
                f"Discovered {len(records)} source candidates",
                metadata={"count": len(records), "by_type": dict(by_type)},
            )
        if self.dry_run:
            return records
        for record in records:
            record.normalized_title = normalize_episode_title(record.source_title)
            self.store.upsert_source(record)
        return records

    def reset_failed_sources(self, *, platform: str | None = None) -> int:
        platform_clause, platform_params = platform_sql_filter(platform or self.only_platform)
        conn = self.store.connect()
        cursor = conn.execute(
            f"""
            UPDATE sources
            SET status = ?, error_message = NULL
            WHERE persona_id = ? AND status = ?{platform_clause}
            """,
            (SourceStatus.PENDING, self.persona_id, SourceStatus.FAILED, *platform_params),
        )
        conn.commit()
        return int(cursor.rowcount)

    def process_pending(
        self,
        *,
        include_failed: bool = False,
        channel_url: str | None = None,
        platform: str | None = None,
    ) -> None:
        rows = self.store.list_pending_sources_ordered(
            include_failed=include_failed,
            channel_url=channel_url,
            platform=platform or self.only_platform,
            limit=self.limit,
        )
        total = len(rows)
        print(f"pending_sources={total}", flush=True)
        conn = self.store.connect()
        for index, row in enumerate(rows, start=1):
            source_id = int(row["id"])
            source_url = row["source_url"]
            source_type = row["source_type"]
            source_title = row["source_title"]
            channel_url = row["channel_url"]
            label = source_title or source_url
            print(f"[{index}/{total}] start {source_type}: {label}", flush=True)
            ctx = get_run_context()
            if ctx:
                ctx.bind_source(
                    source_id=source_id,
                    source_url=source_url,
                    source_title=source_title,
                    source_type=str(source_type),
                    channel_url=str(channel_url) if channel_url else None,
                )
                ctx.event("source_start", f"{source_title or source_url}")
            try:
                if source_type == SourceType.PODCAST:
                    skip, reason = should_skip_podcast_for_youtube_duplicate(conn, self.persona_id, source_title)
                    if skip:
                        self.store.update_source_status(source_id, SourceStatus.SKIPPED, error_message=reason)
                        self.summary.sources_skipped_unchanged += 1
                        print(f"[{index}/{total}] skip: {reason}", flush=True)
                        if ctx:
                            ctx.event("source_skip", reason, source_id=source_id)
                        continue
                self.store.update_source_status(source_id, SourceStatus.PROCESSING)
                if ctx:
                    ctx.event("source_fetch", "Downloading and transcoding content", source_id=source_id)
                document = process_source(
                    self.persona_id,
                    source_type,
                    source_url,
                    self.config.vision_model,
                    self.root,
                    transcription_model=self.config.transcription_model,
                    source_title=source_title,
                )
                upload_date = document.metadata.get("upload_date")
                published_iso = _youtube_upload_date_iso(upload_date)
                self.store.update_source_metadata(
                    source_id,
                    source_title=document.title or source_title,
                    source_date=published_iso,
                    normalized_title=normalize_episode_title(document.title or source_title),
                )
                filtered_text = filter_speaker_content(document.text, self.config.speaker_names)
                content_hash = text_hash(filtered_text)
                change = classify_source_change(
                    existing_status=row["status"],
                    existing_content_hash=row["content_hash"],
                    new_content_hash=content_hash,
                )
                if should_skip_source_processing(change):
                    self.summary.sources_skipped_unchanged += 1
                    print(f"[{index}/{total}] skip: content unchanged", flush=True)
                    if ctx:
                        ctx.event("source_skip", "Content unchanged", source_id=source_id)
                    continue
                if change == SourceChangeKind.UPDATED:
                    self.summary.sources_updated += 1

                print(f"[{index}/{total}] extract: knowledge units ({self.config.extraction_model})", flush=True)
                if ctx:
                    ctx.event("source_extract", "Extracting knowledge units", source_id=source_id)
                units = extract_knowledge_units(
                    persona_id=self.persona_id,
                    source_id=source_id,
                    display_name=self.config.display_name,
                    speaker_names=self.config.speaker_names,
                    title=document.title,
                    source_url=source_url,
                    text=filtered_text,
                    source_nature=document.source_nature,
                    model=self.config.extraction_model,
                    source_index=index,
                    source_total=total,
                )
                if document.visual_assets:
                    units.extend(
                        visual_assets_to_units(
                            persona_id=self.persona_id,
                            source_id=source_id,
                            source_url=source_url,
                            visual_assets=document.visual_assets,
                            source_nature=document.source_nature,
                        )
                    )
                units, novelty_counts = mark_duplicate_units(self.store, units)
                self.summary.units_skipped_duplicate += novelty_counts["duplicate"]
                self.summary.units_repeated_idea += novelty_counts["repeated_idea"]
                self.summary.units_clarification += novelty_counts["clarification"]
                new_unit_ids: list[int] = []
                for unit in units:
                    unit_id = self.store.insert_knowledge_unit(unit)
                    unit.id = unit_id
                    if unit.is_new_information:
                        self.summary.units_created += 1
                        new_unit_ids.append(unit_id)
                if ctx:
                    ctx.event(
                        "source_index",
                        f"Indexing {len(new_unit_ids)} new units",
                        source_id=source_id,
                        metadata={"units_new": len(new_unit_ids), "units_total": len(units)},
                    )
                vector_index = VectorIndex(
                    self.store,
                    model=self.config.embedding_model,
                    root=self.root,
                    qdrant_url=self.config.qdrant_url,
                )
                for unit in units:
                    if unit.id and unit.is_new_information:
                        vector_index.index_unit(unit.id, unit.embedding_text())
                vector_index.index_missing()
                now = datetime.now(timezone.utc).isoformat()
                self.store.update_source_status(
                    source_id,
                    SourceStatus.INDEXED,
                    processed_at=now,
                    content_hash=content_hash,
                )
                self.summary.sources_processed += 1
                print(f"[{index}/{total}] done: units_new={len(new_unit_ids)} units_total={len(units)}", flush=True)
                if ctx:
                    ctx.event(
                        "source_done",
                        f"Indexed: {source_title or source_url}",
                        source_id=source_id,
                        metadata={"units_new": len(new_unit_ids), "units_total": len(units)},
                    )
            except Exception as exc:
                self.summary.errors += 1
                print(f"[{index}/{total}] error: {exc}", flush=True)
                if ctx:
                    ctx.event("source_error", str(exc), source_id=source_id)
                self.store.update_source_status(source_id, SourceStatus.FAILED, error_message=str(exc))
            finally:
                if ctx:
                    ctx.clear_source()

    def run_initial_build(self, *, retry_failed: bool = False) -> PipelineSummary:
        self.initialize()
        if not self.skip_discovery:
            self.discover()
        if not self.dry_run:
            if retry_failed:
                reset_count = self.reset_failed_sources()
                if self.only_platform:
                    print(f"retry_failed_reset={reset_count} only={self.only_platform}")
                else:
                    print(f"retry_failed_reset={reset_count}")
            self.process_pending(include_failed=retry_failed)
        return self.summary

    def run_daily_sync(self, *, retry_failed: bool = False) -> PipelineSummary:
        self.initialize()
        if not self.skip_discovery:
            self.discover()
        if not self.dry_run:
            if retry_failed:
                self.reset_failed_sources()
            self.process_pending(include_failed=retry_failed)
        return self.summary


def _youtube_upload_date_iso(upload_date: str | None) -> str | None:
    if not upload_date or len(upload_date) != 8:
        return None
    year = int(upload_date[0:4])
    month = int(upload_date[4:6])
    day = int(upload_date[6:8])
    return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
