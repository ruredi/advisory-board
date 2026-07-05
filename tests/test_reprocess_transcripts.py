from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from memory_builder.models import SourceStatus
from memory_builder.pipeline.initial_build import MemoryPipeline
from memory_builder.storage.sqlite_store import SQLiteStore


from memory_builder.fetch.downloader import source_slug


def test_reset_indexed_transcripts_includes_spoken_sources(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "hormozi.sqlite"
    social_url = "https://instagram.com/reel/abc123/"
    raw_social = tmp_path / "sources" / "raw" / "hormozi" / source_slug(social_url)
    raw_social.mkdir(parents=True)
    (raw_social / "metadata.json").write_text(
        json.dumps({"transcription_provider": "supadata"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: db,
    )
    monkeypatch.setattr(
        "memory_builder.pipeline.initial_build.project_root",
        lambda: tmp_path,
    )
    store = SQLiteStore("hormozi", tmp_path)
    store.initialize()
    conn = store.connect()
    for source_type, status, source_url in (
        ("youtube", SourceStatus.INDEXED, "https://youtube.com/watch?v=abc"),
        ("podcast", SourceStatus.INDEXED, "https://example.com/ep.mp3"),
        ("social", SourceStatus.INDEXED, social_url),
        ("social", SourceStatus.INDEXED, "https://instagram.com/p/photo123/"),
        ("youtube", SourceStatus.PENDING, "https://youtube.com/watch?v=pending"),
    ):
        conn.execute(
            """
            INSERT INTO sources (persona_id, source_url, source_title, source_type, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("hormozi", source_url, "t", source_type, status),
        )
    conn.commit()

    pipeline = MemoryPipeline("hormozi", tmp_path, skip_discovery=True)
    pipeline.store = store
    reset_ids = pipeline.reset_indexed_transcripts()

    assert len(reset_ids) == 3
    rows = conn.execute(
        "SELECT source_url, status FROM sources WHERE persona_id = ? ORDER BY id",
        ("hormozi",),
    ).fetchall()
    statuses = {(str(row["source_url"]), str(row["status"])) for row in rows}
    assert ("https://youtube.com/watch?v=abc", SourceStatus.PENDING) in statuses
    assert ("https://example.com/ep.mp3", SourceStatus.PENDING) in statuses
    assert ("https://instagram.com/reel/abc123/", SourceStatus.PENDING) in statuses
    assert ("https://instagram.com/p/photo123/", SourceStatus.INDEXED) in statuses
    store.close()


def test_reset_indexed_transcripts_includes_instagram_p_video_from_social_json(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "hormozi.sqlite"
    social_url = "https://instagram.com/p/DaT7kJ_OV4m"
    raw_social = tmp_path / "sources" / "raw" / "hormozi" / source_slug(social_url)
    raw_social.mkdir(parents=True)
    (raw_social / "social.json").write_text(
        json.dumps({"post": {"is_video": True, "shortcode": "DaT7kJ_OV4m"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: db,
    )
    monkeypatch.setattr(
        "memory_builder.pipeline.initial_build.project_root",
        lambda: tmp_path,
    )
    store = SQLiteStore("hormozi", tmp_path)
    store.initialize()
    conn = store.connect()
    conn.execute(
        """
        INSERT INTO sources (persona_id, source_url, source_title, source_type, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("hormozi", social_url, "Reel", "social", SourceStatus.INDEXED),
    )
    conn.commit()

    pipeline = MemoryPipeline("hormozi", tmp_path, skip_discovery=True)
    pipeline.store = store
    reset_ids = pipeline.reset_indexed_transcripts()

    assert reset_ids == [1]
    status = conn.execute("SELECT status FROM sources WHERE id = 1").fetchone()[0]
    assert status == SourceStatus.PENDING
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
