from __future__ import annotations

from unittest.mock import MagicMock, patch

from memory_builder.models import SourceStatus
from memory_builder.pipeline.initial_build import MemoryPipeline
from memory_builder.storage.sqlite_store import SQLiteStore


def test_reset_indexed_transcripts_only_youtube_and_podcast(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "hormozi.sqlite"
    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: db,
    )
    store = SQLiteStore("hormozi", tmp_path)
    store.initialize()
    conn = store.connect()
    for source_type, status in (
        ("youtube", SourceStatus.INDEXED),
        ("podcast", SourceStatus.INDEXED),
        ("social", SourceStatus.INDEXED),
        ("youtube", SourceStatus.PENDING),
    ):
        conn.execute(
            """
            INSERT INTO sources (persona_id, source_url, source_title, source_type, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("hormozi", f"https://example.com/{source_type}-{status}", "t", source_type, status),
        )
    conn.commit()

    pipeline = MemoryPipeline("hormozi", tmp_path, skip_discovery=True)
    pipeline.store = store
    reset_ids = pipeline.reset_indexed_transcripts()

    assert len(reset_ids) == 2
    rows = conn.execute(
        "SELECT source_type, status FROM sources WHERE persona_id = ? ORDER BY id",
        ("hormozi",),
    ).fetchall()
    statuses = {(str(row["source_type"]), str(row["status"])) for row in rows}
    assert ("youtube", SourceStatus.PENDING) in statuses
    assert ("podcast", SourceStatus.PENDING) in statuses
    assert ("social", SourceStatus.INDEXED) in statuses
    store.close()


def test_reprocess_skips_discovery_and_only_processes_reset_ids(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "hormozi.sqlite"
    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: db,
    )
    store = SQLiteStore("hormozi", tmp_path)
    store.initialize()
    conn = store.connect()
    conn.execute(
        """
        INSERT INTO sources (persona_id, source_url, source_title, source_type, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("hormozi", "https://youtube.com/watch?v=abc", "YT", "youtube", SourceStatus.INDEXED),
    )
    yt_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.execute(
        """
        INSERT INTO sources (persona_id, source_url, source_title, source_type, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("hormozi", "https://x.com/status/1", "X post", "social", SourceStatus.PENDING),
    )
    conn.commit()
    store.close()

    pipeline = MemoryPipeline("hormozi", tmp_path, reprocess_transcripts=True)
    pipeline.store = store
    pipeline.initialize()

    with patch.object(pipeline, "discover", MagicMock()) as discover_mock, patch.object(
        pipeline, "process_pending", MagicMock()
    ) as process_mock, patch.object(
        pipeline, "reset_indexed_transcripts", return_value=[yt_id]
    ) as reset_mock:
        pipeline.run_initial_build()

    discover_mock.assert_not_called()
    reset_mock.assert_called_once()
    process_mock.assert_called_once_with(source_ids=[yt_id])
