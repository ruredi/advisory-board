from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from memory_builder.models import KnowledgeUnit, SourceRecord, SourceStatus, json_dumps, json_loads
from memory_builder.paths import db_path, project_root
from memory_builder.pipeline.platform_filter import media_format_sql_filter, platform_sql_filter

STOP_REASON_FINISHED = "finished"
STOP_REASON_INTERRUPTED = "interrupted"
STOP_REASON_FATAL_ERROR = "fatal_error"


class SQLiteStore:
    def __init__(self, persona_id: str, root: Path | None = None) -> None:
        self.persona_id = persona_id
        self.root = root or project_root()
        self.path = db_path(persona_id, self.root)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def initialize(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
        conn = self.connect()
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sources' LIMIT 1"
        ).fetchone():
            self._migrate_schema(conn)
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        self._migrate_schema(conn)
        conn.commit()

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()}
        if "channel_url" not in columns:
            conn.execute("ALTER TABLE sources ADD COLUMN channel_url TEXT")
        if "normalized_title" not in columns:
            conn.execute("ALTER TABLE sources ADD COLUMN normalized_title TEXT")
        if "media_format" not in columns:
            conn.execute("ALTER TABLE sources ADD COLUMN media_format TEXT NOT NULL DEFAULT 'unknown'")
        sync_columns = {row[1] for row in conn.execute("PRAGMA table_info(sync_runs)").fetchall()}
        if sync_columns and "cost_usd" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN cost_usd REAL NOT NULL DEFAULT 0")
        if sync_columns and "last_activity_at" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN last_activity_at TEXT")
            conn.execute(
                "UPDATE sync_runs SET last_activity_at = COALESCE(finished_at, started_at) WHERE last_activity_at IS NULL"
            )
        if sync_columns and "stopped_at" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN stopped_at TEXT")
            conn.execute("UPDATE sync_runs SET stopped_at = finished_at WHERE finished_at IS NOT NULL")
        if sync_columns and "stop_reason" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN stop_reason TEXT")
            conn.execute("UPDATE sync_runs SET stop_reason = 'finished' WHERE finished_at IS NOT NULL")
        if sync_columns and "pid" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN pid INTEGER")
        if sync_columns and "cancel_requested" not in sync_columns:
            conn.execute("ALTER TABLE sync_runs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pipeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id TEXT NOT NULL,
                run_id INTEGER,
                source_id INTEGER,
                stage TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_pipeline_events_run ON pipeline_events(run_id, id);
            CREATE INDEX IF NOT EXISTS idx_pipeline_events_persona_created ON pipeline_events(persona_id, created_at);
            CREATE TABLE IF NOT EXISTS api_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id TEXT NOT NULL,
                run_id INTEGER,
                source_id INTEGER,
                provider TEXT NOT NULL,
                operation TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                api_credits REAL NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                is_estimated INTEGER NOT NULL DEFAULT 1,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_api_usage_persona_created ON api_usage_logs(persona_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_api_usage_run ON api_usage_logs(run_id);
            CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage_logs(persona_id, provider);
            """
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def upsert_source(self, source: SourceRecord) -> int:
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO sources (
                persona_id, source_title, source_url, source_type, source_date,
                discovered_at, processed_at, content_hash, status, speaker,
                source_nature, media_format, raw_path, error_message, channel_url, normalized_title
            ) VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(persona_id, source_url) DO UPDATE SET
                source_title = excluded.source_title,
                source_type = excluded.source_type,
                source_date = COALESCE(excluded.source_date, sources.source_date),
                content_hash = COALESCE(excluded.content_hash, sources.content_hash),
                status = CASE
                    WHEN sources.status IN ('indexed', 'processed', 'skipped') AND excluded.status = 'pending'
                    THEN sources.status
                    ELSE excluded.status
                END,
                speaker = COALESCE(excluded.speaker, sources.speaker),
                source_nature = COALESCE(excluded.source_nature, sources.source_nature),
                media_format = CASE
                    WHEN excluded.media_format IS NOT NULL AND excluded.media_format != 'unknown'
                    THEN excluded.media_format
                    ELSE sources.media_format
                END,
                raw_path = COALESCE(excluded.raw_path, sources.raw_path),
                channel_url = COALESCE(excluded.channel_url, sources.channel_url),
                normalized_title = COALESCE(excluded.normalized_title, sources.normalized_title),
                error_message = excluded.error_message
            """,
            (
                source.persona_id,
                source.source_title,
                source.source_url,
                source.source_type,
                source.source_date,
                source.discovered_at,
                source.processed_at,
                source.content_hash,
                source.status,
                source.speaker,
                source.source_nature,
                source.media_format,
                source.raw_path,
                source.error_message,
                source.channel_url,
                source.normalized_title,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM sources WHERE persona_id = ? AND source_url = ?",
            (source.persona_id, source.source_url),
        ).fetchone()
        return int(row["id"])

    def get_source_by_url(self, source_url: str) -> sqlite3.Row | None:
        return self.connect().execute(
            "SELECT * FROM sources WHERE persona_id = ? AND source_url = ?",
            (self.persona_id, source_url),
        ).fetchone()

    def get_source_by_id(self, source_id: int) -> sqlite3.Row | None:
        return self.connect().execute(
            "SELECT * FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, self.persona_id),
        ).fetchone()

    def delete_source(self, source_id: int) -> list[int]:
        conn = self.connect()
        row = conn.execute(
            "SELECT id FROM sources WHERE id = ? AND persona_id = ?",
            (source_id, self.persona_id),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown source: {source_id}")
        unit_rows = conn.execute(
            "SELECT id FROM knowledge_units WHERE source_id = ?",
            (source_id,),
        ).fetchall()
        unit_ids = [int(item["id"]) for item in unit_rows]
        conn.execute("DELETE FROM sources WHERE id = ? AND persona_id = ?", (source_id, self.persona_id))
        conn.commit()
        return unit_ids

    def source_url_is_new(self, source_url: str) -> bool:
        return self.get_source_by_url(source_url) is None

    def max_source_date_for_channel(self, channel_url: str) -> str | None:
        row = self.connect().execute(
            """
            SELECT MAX(COALESCE(source_date, discovered_at)) AS max_date
            FROM sources
            WHERE persona_id = ? AND channel_url = ?
            """,
            (self.persona_id, channel_url),
        ).fetchone()
        if row is None or row["max_date"] is None:
            return None
        return str(row["max_date"])

    def known_source_urls(self, urls: Iterable[str]) -> set[str]:
        normalized = {normalize_url(url) for url in urls if url}
        if not normalized:
            return set()
        placeholders = ",".join("?" for _ in normalized)
        rows = self.connect().execute(
            f"""
            SELECT source_url FROM sources
            WHERE persona_id = ? AND source_url IN ({placeholders})
            """,
            (self.persona_id, *sorted(normalized)),
        ).fetchall()
        return {str(row["source_url"]) for row in rows}

    def max_source_date_for_platform(self, platform: str) -> str | None:
        clause, params = platform_sql_filter(platform)
        row = self.connect().execute(
            f"""
            SELECT MAX(COALESCE(source_date, discovered_at)) AS max_date
            FROM sources
            WHERE persona_id = ?{clause}
            """,
            (self.persona_id, *params),
        ).fetchone()
        if row is None or row["max_date"] is None:
            return None
        return str(row["max_date"])

    def min_source_date_for_channel(self, channel_url: str) -> str | None:
        row = self.connect().execute(
            """
            SELECT MIN(COALESCE(source_date, discovered_at)) AS min_date
            FROM sources
            WHERE persona_id = ? AND channel_url = ?
            """,
            (self.persona_id, channel_url),
        ).fetchone()
        if row is None or row["min_date"] is None:
            return None
        return str(row["min_date"])

    def min_source_date_for_platform(self, platform: str) -> str | None:
        clause, params = platform_sql_filter(platform)
        row = self.connect().execute(
            f"""
            SELECT MIN(COALESCE(source_date, discovered_at)) AS min_date
            FROM sources
            WHERE persona_id = ?{clause}
            """,
            (self.persona_id, *params),
        ).fetchone()
        if row is None or row["min_date"] is None:
            return None
        return str(row["min_date"])

    def list_source_urls_for_platform(self, platform: str) -> set[str]:
        clause, params = platform_sql_filter(platform)
        rows = self.connect().execute(
            f"""
            SELECT source_url FROM sources
            WHERE persona_id = ?{clause}
            """,
            (self.persona_id, *params),
        ).fetchall()
        return {str(row["source_url"]) for row in rows}

    def list_source_urls_for_channel(self, channel_url: str) -> set[str]:
        rows = self.connect().execute(
            """
            SELECT source_url FROM sources
            WHERE persona_id = ? AND channel_url = ?
            """,
            (self.persona_id, channel_url),
        ).fetchall()
        return {str(row["source_url"]) for row in rows}

    def list_sources(self, status: str | None = None, limit: int | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM sources WHERE persona_id = ?"
        params: list[object] = [self.persona_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id ASC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        return list(self.connect().execute(query, params).fetchall())

    def list_pending_sources_ordered(
        self,
        *,
        include_failed: bool = False,
        channel_url: str | None = None,
        platform: str | None = None,
        media_format: str | None = None,
        limit: int | None = None,
    ) -> list[sqlite3.Row]:
        statuses = [SourceStatus.PENDING]
        if include_failed:
            statuses.append(SourceStatus.FAILED)
        placeholders = ",".join("?" for _ in statuses)
        query = f"""
            SELECT * FROM sources
            WHERE persona_id = ?
              AND status IN ({placeholders})
        """
        params: list[object] = [self.persona_id, *statuses]
        if channel_url:
            query += " AND channel_url = ?"
            params.append(channel_url)
        platform_clause, platform_params = platform_sql_filter(platform)
        query += platform_clause
        params.extend(platform_params)
        media_clause, media_params = media_format_sql_filter(media_format)
        query += media_clause
        params.extend(media_params)
        query += """
            ORDER BY
                CASE source_type
                    WHEN 'youtube' THEN 1
                    WHEN 'podcast' THEN 2
                    ELSE 3
                END,
                source_date IS NULL,
                source_date DESC,
                id ASC
        """
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return list(self.connect().execute(query, params).fetchall())

    def list_sources_by_ids(self, source_ids: list[int], *, limit: int | None = None) -> list[sqlite3.Row]:
        if not source_ids:
            return []
        placeholders = ",".join("?" for _ in source_ids)
        query = f"""
            SELECT * FROM sources
            WHERE persona_id = ?
              AND id IN ({placeholders})
            ORDER BY
                CASE source_type
                    WHEN 'youtube' THEN 1
                    WHEN 'podcast' THEN 2
                    ELSE 3
                END,
                source_date IS NULL,
                source_date DESC,
                id ASC
        """
        params: list[object] = [self.persona_id, *source_ids]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return list(self.connect().execute(query, params).fetchall())

    def update_source_metadata(
        self,
        source_id: int,
        *,
        source_title: str | None = None,
        source_date: str | None = None,
        normalized_title: str | None = None,
        source_nature: str | None = None,
        media_format: str | None = None,
    ) -> None:
        conn = self.connect()
        normalized_media = media_format if media_format and media_format != "unknown" else None
        conn.execute(
            """
            UPDATE sources SET
                source_title = COALESCE(?, source_title),
                source_date = COALESCE(?, source_date),
                normalized_title = COALESCE(?, normalized_title),
                source_nature = COALESCE(?, source_nature),
                media_format = COALESCE(?, media_format)
            WHERE id = ?
            """,
            (source_title, source_date, normalized_title, source_nature, normalized_media, source_id),
        )
        conn.commit()

    def update_source_status(
        self,
        source_id: int,
        status: str,
        *,
        processed_at: str | None = None,
        raw_path: str | None = None,
        content_hash: str | None = None,
        error_message: str | None = None,
    ) -> None:
        conn = self.connect()
        conn.execute(
            """
            UPDATE sources SET
                status = ?,
                processed_at = COALESCE(?, processed_at),
                raw_path = COALESCE(?, raw_path),
                content_hash = COALESCE(?, content_hash),
                error_message = ?
            WHERE id = ?
            """,
            (status, processed_at, raw_path, content_hash, error_message, source_id),
        )
        conn.commit()

    def insert_knowledge_unit(self, unit: KnowledgeUnit) -> int:
        row = unit.to_row()
        conn = self.connect()
        cursor = conn.execute(
            """
            INSERT INTO knowledge_units (
                persona_id, source_id, content_type, chunk_text, visual_description,
                topics, frameworks, processes, steps, concepts, advice_contexts,
                examples, quotes, confidence, retrieval_priority, is_new_information,
                duplicate_of, speaker, source_nature, evidence_type, content_fingerprint
            ) VALUES (
                :persona_id, :source_id, :content_type, :chunk_text, :visual_description,
                :topics, :frameworks, :processes, :steps, :concepts, :advice_contexts,
                :examples, :quotes, :confidence, :retrieval_priority, :is_new_information,
                :duplicate_of, :speaker, :source_nature, :evidence_type, :content_fingerprint
            )
            """,
            {**row, "content_fingerprint": content_fingerprint(unit)},
        )
        conn.commit()
        return int(cursor.lastrowid)

    def find_unit_by_fingerprint(self, fingerprint: str) -> int | None:
        row = self.connect().execute(
            "SELECT id FROM knowledge_units WHERE persona_id = ? AND content_fingerprint = ?",
            (self.persona_id, fingerprint),
        ).fetchone()
        return int(row["id"]) if row else None

    def list_knowledge_units(self, limit: int | None = None) -> list[sqlite3.Row]:
        query = "SELECT * FROM knowledge_units WHERE persona_id = ? ORDER BY id ASC"
        params: list[object] = [self.persona_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        return list(self.connect().execute(query, params).fetchall())

    def row_to_knowledge_unit(self, row: sqlite3.Row) -> KnowledgeUnit:
        return KnowledgeUnit(
            id=row["id"],
            persona_id=row["persona_id"],
            source_id=row["source_id"],
            content_type=row["content_type"],
            chunk_text=row["chunk_text"],
            visual_description=row["visual_description"],
            topics=json_loads(row["topics"]),
            frameworks=json_loads(row["frameworks"]),
            processes=json_loads(row["processes"]),
            steps=json_loads(row["steps"]),
            concepts=json_loads(row["concepts"]),
            advice_contexts=json_loads(row["advice_contexts"]),
            examples=json_loads(row["examples"]),
            quotes=json_loads(row["quotes"]),
            confidence=row["confidence"],
            retrieval_priority=row["retrieval_priority"],
            is_new_information=bool(row["is_new_information"]),
            duplicate_of=row["duplicate_of"],
            speaker=row["speaker"],
            source_nature=row["source_nature"],
            evidence_type=row["evidence_type"],
        )

    def save_embedding(self, knowledge_unit_id: int, model: str, vector: list[float]) -> None:
        import struct

        blob = struct.pack(f"{len(vector)}f", *vector)
        conn = self.connect()
        conn.execute(
            """
            INSERT INTO embeddings (knowledge_unit_id, model, embedding, dimensions)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(knowledge_unit_id) DO UPDATE SET
                model = excluded.model,
                embedding = excluded.embedding,
                dimensions = excluded.dimensions,
                created_at = datetime('now')
            """,
            (knowledge_unit_id, model, blob, len(vector)),
        )
        conn.commit()

    def load_embeddings(self) -> list[tuple[int, list[float]]]:
        import struct

        rows = self.connect().execute(
            """
            SELECT e.knowledge_unit_id, e.embedding, e.dimensions
            FROM embeddings e
            JOIN knowledge_units k ON k.id = e.knowledge_unit_id
            WHERE k.persona_id = ? AND k.is_new_information = 1 AND k.duplicate_of IS NULL
            """,
            (self.persona_id,),
        ).fetchall()
        result: list[tuple[int, list[float]]] = []
        for row in rows:
            dims = int(row["dimensions"])
            vector = list(struct.unpack(f"{dims}f", row["embedding"]))
            result.append((int(row["knowledge_unit_id"]), vector))
        return result

    def start_sync_run(self) -> int:
        from memory_builder.telemetry.run_watchdog import close_stale_runs_for_persona

        close_stale_runs_for_persona(self, self.persona_id)
        cursor = self.connect().execute(
            """
            INSERT INTO sync_runs (persona_id, last_activity_at)
            VALUES (?, datetime('now'))
            """,
            (self.persona_id,),
        )
        self.connect().commit()
        return int(cursor.lastrowid)

    def set_run_pid(self, run_id: int, pid: int) -> None:
        self.connect().execute(
            "UPDATE sync_runs SET pid = ? WHERE id = ? AND finished_at IS NULL",
            (pid, run_id),
        )
        self.connect().commit()

    def get_run_pid(self, run_id: int) -> int | None:
        row = self.connect().execute(
            "SELECT pid FROM sync_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None or row["pid"] is None:
            return None
        return int(row["pid"])

    def request_run_cancel(self, run_id: int) -> bool:
        updated = self.connect().execute(
            """
            UPDATE sync_runs
            SET cancel_requested = 1
            WHERE id = ? AND finished_at IS NULL
            """,
            (run_id,),
        )
        self.connect().commit()
        return updated.rowcount > 0

    def is_run_cancel_requested(self, run_id: int) -> bool:
        row = self.connect().execute(
            "SELECT cancel_requested FROM sync_runs WHERE id = ? AND finished_at IS NULL",
            (run_id,),
        ).fetchone()
        return row is not None and bool(row["cancel_requested"])

    def touch_run_activity(self, run_id: int) -> None:
        # Heartbeat runs on a background thread; use a short-lived connection instead of self._conn.
        conn = sqlite3.connect(self.path, check_same_thread=False)
        try:
            conn.execute(
                """
                UPDATE sync_runs
                SET last_activity_at = datetime('now')
                WHERE id = ? AND finished_at IS NULL
                """,
                (run_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_run_stopped(
        self,
        run_id: int,
        *,
        reason: str,
        event_stage: str = "run_interrupted",
        message: str | None = None,
        summary: dict[str, int | str] | None = None,
    ) -> bool:
        row = self.connect().execute(
            """
            SELECT finished_at, last_activity_at, started_at, persona_id
            FROM sync_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None or row["finished_at"] is not None:
            return False
        stopped_at = row["last_activity_at"] or row["started_at"]
        cost_row = self.connect().execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM api_usage_logs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        run_cost = float(cost_row["total"]) if cost_row else 0.0
        if summary:
            self.connect().execute(
                """
                UPDATE sync_runs
                SET sources_discovered = ?,
                    sources_processed = ?,
                    units_created = ?,
                    units_skipped_duplicate = ?,
                    errors = ?,
                    summary = ?
                WHERE id = ? AND finished_at IS NULL
                """,
                (
                    summary.get("sources_discovered", 0),
                    summary.get("sources_processed", 0),
                    summary.get("units_created", 0),
                    summary.get("units_skipped_duplicate", 0),
                    summary.get("errors", 0),
                    json_dumps(summary),
                    run_id,
                ),
            )
        updated = self.connect().execute(
            """
            UPDATE sync_runs
            SET finished_at = ?,
                stopped_at = ?,
                stop_reason = ?,
                cost_usd = ?,
                last_activity_at = COALESCE(last_activity_at, started_at)
            WHERE id = ? AND finished_at IS NULL
            """,
            (stopped_at, stopped_at, reason, run_cost, run_id),
        )
        if updated.rowcount == 0:
            return False
        event_message = message or f"Pipeline run {run_id} stopped ({reason})"
        self.log_pipeline_event(
            persona_id=str(row["persona_id"]),
            run_id=run_id,
            stage=event_stage,
            message=event_message,
            metadata={"stop_reason": reason, "stopped_at": stopped_at},
        )
        self.connect().commit()
        return True

    def mark_run_interrupted(self, run_id: int, *, reason: str = STOP_REASON_INTERRUPTED) -> bool:
        return self.mark_run_stopped(
            run_id,
            reason=reason,
            event_stage="run_interrupted",
            message=f"Pipeline run {run_id} stopped without finishing",
        )

    def is_run_open(self, run_id: int) -> bool:
        row = self.connect().execute(
            "SELECT finished_at FROM sync_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return row is not None and row["finished_at"] is None

    def update_sync_run_discovered(self, run_id: int, sources_discovered: int) -> None:
        self.connect().execute(
            """
            UPDATE sync_runs
            SET sources_discovered = ?, last_activity_at = datetime('now')
            WHERE id = ?
            """,
            (sources_discovered, run_id),
        )
        self.connect().commit()

    def finish_sync_run(self, run_id: int, summary: dict[str, int | str]) -> None:
        cost_row = self.connect().execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM api_usage_logs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        run_cost = float(cost_row["total"]) if cost_row else 0.0
        self.connect().execute(
            """
            UPDATE sync_runs SET
                finished_at = datetime('now'),
                stopped_at = datetime('now'),
                stop_reason = 'finished',
                last_activity_at = datetime('now'),
                sources_discovered = ?,
                sources_processed = ?,
                units_created = ?,
                units_skipped_duplicate = ?,
                errors = ?,
                cost_usd = ?,
                summary = ?
            WHERE id = ?
            """,
            (
                summary.get("sources_discovered", 0),
                summary.get("sources_processed", 0),
                summary.get("units_created", 0),
                summary.get("units_skipped_duplicate", 0),
                summary.get("errors", 0),
                run_cost,
                str(summary),
                run_id,
            ),
        )
        self.connect().commit()

    def log_pipeline_event(
        self,
        *,
        persona_id: str,
        run_id: int | None,
        stage: str,
        message: str,
        source_id: int | None = None,
        metadata: dict | None = None,
    ) -> int:
        cursor = self.connect().execute(
            """
            INSERT INTO pipeline_events (persona_id, run_id, source_id, stage, message, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (persona_id, run_id, source_id, stage, message, json_dumps(metadata or {})),
        )
        if run_id is not None:
            self.connect().execute(
                """
                UPDATE sync_runs
                SET last_activity_at = datetime('now')
                WHERE id = ? AND finished_at IS NULL
                """,
                (run_id,),
            )
        self.connect().commit()
        return int(cursor.lastrowid)

    def log_api_usage(
        self,
        *,
        persona_id: str,
        run_id: int | None,
        source_id: int | None,
        provider: str,
        operation: str,
        model: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        api_credits: float = 0.0,
        cost_usd: float = 0.0,
        is_estimated: bool = True,
        metadata: dict | None = None,
    ) -> int:
        cursor = self.connect().execute(
            """
            INSERT INTO api_usage_logs (
                persona_id, run_id, source_id, provider, operation, model,
                input_tokens, output_tokens, api_credits, cost_usd, is_estimated, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                persona_id,
                run_id,
                source_id,
                provider,
                operation,
                model,
                input_tokens,
                output_tokens,
                api_credits,
                cost_usd,
                1 if is_estimated else 0,
                json_dumps(metadata or {}),
            ),
        )
        self.connect().commit()
        return int(cursor.lastrowid)


def content_fingerprint(unit: KnowledgeUnit) -> str:
    normalized = re.sub(r"\s+", " ", unit.chunk_text.strip().lower())
    payload = f"{unit.content_type}|{normalized}|{'|'.join(unit.steps)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse("https://" + url.strip())
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query, keep_blank_values=False)
    if "youtube.com" in netloc or "youtu.be" in netloc:
        video_id = None
        if netloc == "youtu.be":
            video_id = path.lstrip("/").split("/")[0]
        elif path.startswith("/watch"):
            video_id = query.get("v", [None])[0]
        elif path.startswith("/shorts/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else None
        elif path.startswith("/live/"):
            video_id = path.split("/")[2] if len(path.split("/")) > 2 else None
        if video_id:
            return f"https://youtube.com/watch?v={video_id}"
    clean_query = urlencode({k: v[0] for k, v in sorted(query.items()) if v}, doseq=False)
    return urlunparse((parsed.scheme.lower(), netloc, path, "", clean_query, ""))


def text_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
