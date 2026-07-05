from __future__ import annotations

import logging
import time
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
from memory_builder.discovery.source_emit import OnSourceRecord
from memory_builder.extraction.extractor import extract_knowledge_units
from memory_builder.extraction.visual_units import visual_assets_to_units
from memory_builder.models import SourceNature, SourceRecord, SourceStatus, SourceType
from memory_builder.paths import project_root
from memory_builder.pipeline.fatal_errors import (
    FatalErrorTracker,
    PipelineCancelledError,
    PipelineFatalError,
    is_transient_error,
)
from memory_builder.pipeline.platform_filter import media_format_sql_filter, platform_sql_filter, source_url_matches_platform
from memory_builder.processors import process_source
from memory_builder.processors.social_media_enrichment import should_reprocess_social_transcript
from memory_builder.processors.transcript_status import load_source_metadata
from memory_builder.processors.transcript_storage import load_transcript_segments
from memory_builder.storage.segment_index import SegmentIndex
from memory_builder.source_registry import approved_scraper_profiles, load_approved
from memory_builder.storage.sqlite_store import SQLiteStore, STOP_REASON_FATAL_ERROR, text_hash
from memory_builder.storage.vector_index import VectorIndex
from memory_builder.telemetry.context import get_run_context


log = logging.getLogger(__name__)
from memory_builder.telemetry.discovery_events import discovery_log
from memory_builder.telemetry.run_cancel import abort_if_run_cancelled


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
        media_format: str | None = None,
        skip_discovery: bool = False,
        discovery_limit: int | None = None,
        reprocess_transcripts: bool = False,
    ) -> None:
        self.root = root or project_root()
        self.persona_id = persona_id
        self.config = load_persona_config(persona_id, self.root)
        self.store = SQLiteStore(persona_id, self.root)
        self.limit = limit
        self.dry_run = dry_run
        self.only_platform = only_platform
        self.media_format = media_format
        self.skip_discovery = skip_discovery or reprocess_transcripts
        self.discovery_limit = discovery_limit
        self.reprocess_transcripts = reprocess_transcripts
        self.summary = PipelineSummary()

    def summary_dict(self) -> dict[str, int | str]:
        return {
            "sources_discovered": self.summary.sources_discovered,
            "sources_processed": self.summary.sources_processed,
            "sources_skipped_unchanged": self.summary.sources_skipped_unchanged,
            "sources_updated": self.summary.sources_updated,
            "units_created": self.summary.units_created,
            "units_skipped_duplicate": self.summary.units_skipped_duplicate,
            "units_repeated_idea": self.summary.units_repeated_idea,
            "units_clarification": self.summary.units_clarification,
            "errors": self.summary.errors,
            "only_platform": self.only_platform or "",
        }

    def initialize(self) -> None:
        self.store.initialize()

    def _persist_discovered_record(self, record: SourceRecord) -> bool:
        """Ment egy új forrást azonnal. False = már ismert URL."""
        if not self.store.source_url_is_new(record.source_url):
            return False
        record.normalized_title = normalize_episode_title(record.source_title)
        self.store.upsert_source(record)
        self.summary.sources_discovered += 1
        label = (record.source_title or record.source_url)[:120]
        count = self.summary.sources_discovered
        if count <= 3 or count % 10 == 0:
            discovery_log(f"Mentve ({count}): {label}")
        ctx = get_run_context()
        if ctx:
            if count <= 3 or count % 10 == 0:
                ctx.event(
                    "discovery",
                    f"Új forrás mentve ({count}): {label}",
                    metadata={
                        "source_url": record.source_url,
                        "count": count,
                    },
                )
            self.store.update_sync_run_discovered(ctx.run_id, count)
        return True

    def _make_discovery_callback(self, records: list[SourceRecord]) -> OnSourceRecord:
        """Azonnali mentés (vagy dry-run gyűjtés) forrásonként; False = állj meg (limit)."""
        stop_discovery = False

        def on_record(record: SourceRecord) -> bool:
            nonlocal stop_discovery
            if stop_discovery:
                return False
            if (
                self.discovery_limit
                and self.discovery_limit > 0
                and len(records) >= self.discovery_limit
            ):
                stop_discovery = True
                return False
            if self.dry_run:
                records.append(record)
                self.summary.sources_discovered = len(records)
                return True
            if self._persist_discovered_record(record):
                records.append(record)
            return True

        return on_record

    def discover(self) -> list[SourceRecord]:
        discovery_log("Forrás keresés indul")
        ctx = get_run_context()
        if ctx:
            ctx.event("discovery", "Source discovery started")
        records: list[SourceRecord] = []
        on_record = self._make_discovery_callback(records)
        store = None if self.dry_run else self.store

        seed_count = 0
        for record in discover_seed_sources(self.persona_id, self.config.seed_link_files):
            if not source_url_matches_platform(record.source_url, record.source_type, self.only_platform):
                continue
            if on_record(record):
                seed_count += 1
        if seed_count:
            discovery_log(f"Seed linkek: {seed_count} jelölt")
        registry = load_channels(self.persona_id, self.root)
        discover_channels(
            self.persona_id,
            registry,
            store=store,
            only_platform=self.only_platform,
            on_record=on_record,
            after_channel=(lambda: save_channels(registry, self.root)) if not self.dry_run else None,
        )
        approved = load_approved(self.persona_id, self.root)
        if approved:
            social_profiles = approved_scraper_profiles(approved)
        else:
            social_profiles = self.config.social_profiles
        discover_social_sources(
            self.persona_id,
            social_profiles,
            only_platform=self.only_platform,
            store=store,
            discovery_limit=self.discovery_limit,
            on_record=on_record,
            collected_count=(lambda: len(records)),
        )
        discovery_log(f"Összesen {len(records)} új forrás")
        if ctx:
            from collections import Counter

            by_type = Counter(str(record.source_type) for record in records)
            ctx.event(
                "discovery",
                f"Discovered {len(records)} new source candidates",
                metadata={"count": len(records), "by_type": dict(by_type)},
            )
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

    def reset_indexed_transcripts(self, *, platform: str | None = None) -> list[int]:
        platform_clause, platform_params = platform_sql_filter(platform or self.only_platform)
        media_clause, media_params = media_format_sql_filter(self.media_format)
        conn = self.store.connect()
        rows = conn.execute(
            f"""
            SELECT id, source_type, source_url FROM sources
            WHERE persona_id = ? AND status = ?
              AND source_type IN ('youtube', 'podcast', 'social'){platform_clause}{media_clause}
            ORDER BY
                CASE source_type
                    WHEN 'youtube' THEN 1
                    WHEN 'podcast' THEN 2
                    WHEN 'social' THEN 3
                    ELSE 4
                END,
                source_date IS NULL,
                source_date DESC,
                id ASC
            """,
            (self.persona_id, SourceStatus.INDEXED, *platform_params, *media_params),
        ).fetchall()
        source_ids: list[int] = []
        for row in rows:
            source_type = str(row["source_type"])
            source_url = str(row["source_url"])
            if source_type == "social":
                metadata = load_source_metadata(self.persona_id, source_url, self.root)
                if not should_reprocess_social_transcript(
                    self.persona_id,
                    source_url,
                    self.root,
                    metadata=metadata,
                ):
                    continue
            source_ids.append(int(row["id"]))
        if not source_ids:
            return []
        placeholders = ",".join("?" for _ in source_ids)
        conn.execute(
            f"""
            UPDATE sources
            SET status = ?, error_message = NULL, content_hash = NULL
            WHERE id IN ({placeholders})
            """,
            (SourceStatus.PENDING, *source_ids),
        )
        conn.commit()
        return source_ids

    def _run_reprocess_transcripts(self) -> None:
        reset_ids = self.reset_indexed_transcripts()
        if self.only_platform:
            print(f"reprocess_transcripts_reset={len(reset_ids)} only={self.only_platform}", flush=True)
        else:
            print(f"reprocess_transcripts_reset={len(reset_ids)}", flush=True)
        if not reset_ids:
            print("reprocess_transcripts: nincs indexed spoken forrás", flush=True)
            return
        self.process_pending(source_ids=reset_ids)

    def process_pending(
        self,
        *,
        include_failed: bool = False,
        channel_url: str | None = None,
        platform: str | None = None,
        source_ids: list[int] | None = None,
    ) -> None:
        if source_ids is not None:
            rows = self.store.list_sources_by_ids(source_ids, limit=self.limit)
        else:
            rows = self.store.list_pending_sources_ordered(
                include_failed=include_failed,
                channel_url=channel_url,
                platform=platform or self.only_platform,
                media_format=self.media_format,
                limit=self.limit,
            )
        total = len(rows)
        print(f"pending_sources={total}", flush=True)
        conn = self.store.connect()
        fatal_tracker = FatalErrorTracker()
        for index, row in enumerate(rows, start=1):
            ctx = get_run_context()
            if ctx:
                abort_if_run_cancelled(self.store, ctx.run_id, summary=self.summary_dict())
            source_id = int(row["id"])
            source_url = row["source_url"]
            source_type = row["source_type"]
            source_title = row["source_title"]
            channel_url = row["channel_url"]
            label = source_title or source_url
            print(f"[{index}/{total}] start {source_type}: {label}", flush=True)
            if ctx:
                ctx.bind_source(
                    source_id=source_id,
                    source_url=source_url,
                    source_title=source_title,
                    source_type=str(source_type),
                    channel_url=str(channel_url) if channel_url else None,
                )
                ctx.event("source_start", f"{source_title or source_url}")
            source_exc: Exception | None = None
            try:
                for source_attempt in range(3):
                    try:
                        if source_type == SourceType.PODCAST:
                            skip, reason = should_skip_podcast_for_youtube_duplicate(
                                conn, self.persona_id, source_title
                            )
                            if skip:
                                self.store.update_source_status(
                                    source_id, SourceStatus.SKIPPED, error_message=reason
                                )
                                self.summary.sources_skipped_unchanged += 1
                                print(f"[{index}/{total}] skip: {reason}", flush=True)
                                if ctx:
                                    ctx.event("source_skip", reason, source_id=source_id)
                                source_exc = None
                                break
                        self.store.update_source_status(source_id, SourceStatus.PROCESSING)
                        if ctx:
                            ctx.event(
                                "source_fetch",
                                "Downloading and transcoding content",
                                source_id=source_id,
                            )
                        document = process_source(
                            self.persona_id,
                            source_type,
                            source_url,
                            self.config.vision_model,
                            self.root,
                            transcription_model=self.config.transcription_model,
                            source_title=source_title,
                            channel_url=str(channel_url) if channel_url else "",
                            display_name=self.config.display_name,
                            speaker_names=self.config.speaker_names,
                            speaker_labeled_transcription=self.config.speaker_labeled_transcription,
                            allow_unlabeled_fallback=self.config.allow_unlabeled_fallback,
                        )
                        upload_date = document.metadata.get("upload_date")
                        published_iso = _youtube_upload_date_iso(upload_date)
                        self.store.update_source_metadata(
                            source_id,
                            source_title=document.title or source_title,
                            source_date=published_iso,
                            normalized_title=normalize_episode_title(document.title or source_title),
                            source_nature=document.source_nature,
                            media_format=document.media_format,
                        )
                        filtered_text = (
                            document.text
                            if document.source_nature == SourceNature.WRITTEN
                            else filter_speaker_content(
                                document.text,
                                self.config.speaker_names,
                                display_name=self.config.display_name,
                            )
                        )
                        if not filtered_text.strip():
                            raise RuntimeError(
                                f"No extractable content after speaker filtering: {source_url}"
                            )
                        content_hash = text_hash(filtered_text)
                        change = classify_source_change(
                            existing_status=row["status"],
                            existing_content_hash=row["content_hash"],
                            new_content_hash=content_hash,
                        )
                        if should_skip_source_processing(change):
                            self.store.update_source_status(
                                source_id,
                                SourceStatus.INDEXED,
                                content_hash=content_hash,
                            )
                            self.summary.sources_skipped_unchanged += 1
                            print(f"[{index}/{total}] skip: content unchanged", flush=True)
                            if ctx:
                                ctx.event("source_skip", "Content unchanged", source_id=source_id)
                            source_exc = None
                            break
                        if change == SourceChangeKind.UPDATED:
                            self.summary.sources_updated += 1

                        print(
                            f"[{index}/{total}] extract: knowledge units ({self.config.extraction_model})",
                            flush=True,
                        )
                        if ctx:
                            ctx.event(
                                "source_extract",
                                "Extracting knowledge units",
                                source_id=source_id,
                            )
                        segments_path = document.metadata.get("path_transcript_segments.json")
                        segments = load_transcript_segments(segments_path) if segments_path else None
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
                            segments=segments,
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
                        segment_index = SegmentIndex(vector_index)
                        for unit in units:
                            if unit.id and unit.is_new_information:
                                try:
                                    vector_index.index_unit(unit.id, unit.embedding_text())
                                except Exception as index_exc:
                                    log.warning("Failed to index unit %s: %s", unit.id, index_exc)
                        if segments is not None:
                            try:
                                indexed_segments = segment_index.index_source_segments(
                                    source_id=source_id,
                                    segments=segments,
                                    source_url=source_url,
                                    source_title=document.title or source_title,
                                )
                                if ctx:
                                    ctx.event(
                                        "source_segment_index",
                                        f"Indexed {indexed_segments} transcript segments",
                                        source_id=source_id,
                                        metadata={"segment_count": indexed_segments},
                                    )
                            except Exception as index_exc:
                                log.warning("Failed to index segments for source %s: %s", source_id, index_exc)
                        try:
                            vector_index.index_missing()
                        except Exception as index_exc:
                            log.warning("index_missing failed: %s", index_exc)
                        now = datetime.now(timezone.utc).isoformat()
                        self.store.update_source_status(
                            source_id,
                            SourceStatus.INDEXED,
                            processed_at=now,
                            content_hash=content_hash,
                        )
                        self.summary.sources_processed += 1
                        print(
                            f"[{index}/{total}] done: units_new={len(new_unit_ids)} units_total={len(units)}",
                            flush=True,
                        )
                        fatal_tracker.reset()
                        if ctx:
                            ctx.event(
                                "source_done",
                                f"Indexed: {source_title or source_url}",
                                source_id=source_id,
                                metadata={"units_new": len(new_unit_ids), "units_total": len(units)},
                            )
                        source_exc = None
                        break
                    except Exception as exc:
                        source_exc = exc
                        if source_attempt < 2 and is_transient_error(exc):
                            delay_seconds = 5 * (source_attempt + 1)
                            print(
                                f"[{index}/{total}] retry {source_attempt + 2}/3 in {delay_seconds}s: {exc}",
                                flush=True,
                            )
                            time.sleep(delay_seconds)
                            continue
                        break
                if source_exc is not None:
                    exc = source_exc
                    self.summary.errors += 1
                    print(f"[{index}/{total}] error: {exc}", flush=True)
                    if ctx:
                        ctx.event("source_error", str(exc), source_id=source_id)
                    self.store.update_source_status(source_id, SourceStatus.FAILED, error_message=str(exc))
                    if fatal_tracker.record(exc):
                        abort_message = (
                            f"Pipeline stopped after repeated fatal errors (last: {exc})"
                        )
                        print(abort_message, flush=True)
                        if ctx:
                            self.store.mark_run_stopped(
                                ctx.run_id,
                                reason=STOP_REASON_FATAL_ERROR,
                                event_stage="run_aborted",
                                message=abort_message,
                                summary=self.summary_dict(),
                            )
                        raise PipelineFatalError(abort_message) from exc
            finally:
                if ctx:
                    ctx.clear_source()

    def run_initial_build(self, *, retry_failed: bool = False, discover_only: bool = False) -> PipelineSummary:
        self.initialize()
        if not self.skip_discovery:
            self.discover()
        if self.dry_run or discover_only:
            return self.summary
        if self.reprocess_transcripts:
            self._run_reprocess_transcripts()
            return self.summary
        if retry_failed:
            reset_count = self.reset_failed_sources()
            if self.only_platform:
                print(f"retry_failed_reset={reset_count} only={self.only_platform}")
            else:
                print(f"retry_failed_reset={reset_count}")
        self.process_pending(include_failed=retry_failed)
        return self.summary

    def run_daily_sync(self, *, retry_failed: bool = False, discover_only: bool = False) -> PipelineSummary:
        self.initialize()
        if not self.skip_discovery:
            self.discover()
        if self.dry_run or discover_only:
            return self.summary
        if self.reprocess_transcripts:
            self._run_reprocess_transcripts()
            return self.summary
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
