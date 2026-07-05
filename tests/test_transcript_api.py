from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from memory_builder.models import json_dumps
from memory_builder.storage.sqlite_store import SQLiteStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "memory" / "hormozi.sqlite"
    db.parent.mkdir(parents=True)
    processed = tmp_path / "processed" / "slug123"
    processed.mkdir(parents=True)
    (processed / "document.txt").write_text("Alex Hormozi:\nHello world", encoding="utf-8")
    (processed / "transcript_segments.json").write_text(
        json.dumps(
            {
                "display_name": "Alex Hormozi",
                "transcription_mode": "diarized",
                "segments": [
                    {
                        "segment_id": "seg-1",
                        "speaker": "Alex Hormozi",
                        "speaker_type": "target",
                        "text": "Hello world",
                        "start_seconds": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    raw = tmp_path / "raw" / "slug123"
    raw.mkdir(parents=True)
    (raw / "metadata.json").write_text(
        json.dumps({"transcription_mode": "diarized"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "memory_builder.storage.sqlite_store.db_path",
        lambda persona_id, root=None: tmp_path / "memory" / f"{persona_id}.sqlite",
    )
    monkeypatch.setattr(
        "api.sources.processed_dir_for_source",
        lambda persona_id, source_url, root=None: processed,
    )
    monkeypatch.setattr(
        "api.sources.load_source_metadata",
        lambda persona_id, source_url, root=None: {"transcription_mode": "diarized"},
    )

    store = SQLiteStore("hormozi", tmp_path)
    store.initialize()
    conn = store.connect()
    conn.execute(
        """
        INSERT INTO sources (
            persona_id, source_url, source_title, source_type, status
        ) VALUES (?, ?, ?, ?, ?)
        """,
        ("hormozi", "https://example.com/ep", "Episode", "podcast", "indexed"),
    )
    source_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.execute(
        """
        INSERT INTO knowledge_units (
            persona_id, source_id, content_type, chunk_text, topics, frameworks, processes,
            steps, concepts, advice_contexts, examples, quotes, confidence, retrieval_priority,
            is_new_information, duplicate_of, speaker, source_nature, evidence_type, visual_description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "hormozi",
            source_id,
            "quote",
            "Pricing advice",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            "[]",
            json_dumps(
                [
                    {
                        "text": "Hello world",
                        "is_verbatim": True,
                        "speaker": "Alex Hormozi",
                        "source_link": "https://example.com/ep?t=1",
                        "segment_id": "seg-1",
                        "start_seconds": 1,
                    }
                ]
            ),
            "strong",
            70,
            1,
            None,
            "Alex Hormozi",
            "natural_spoken",
            "source_supported",
            "",
        ),
    )
    unit_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    store.close()

    test_client = TestClient(app)
    test_client.test_source_id = source_id
    test_client.test_unit_id = unit_id
    return test_client


def test_source_detail_includes_transcript_status(client):
    source_id = client.test_source_id
    response = client.get(f"/personas/hormozi/sources/{source_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["transcript_status"] == "labeled"
    variants = {item["key"]: item for item in body["transcript_variants"]}
    assert variants["segments"]["available"] is True
    assert variants["labeled"]["available"] is True
    assert any(variant["key"] == "document" for variant in body["transcript_variants"])


def test_labeled_variant_runtime_render_without_legacy_file(client):
    source_id = client.test_source_id
    response = client.get(f"/personas/hormozi/sources/{source_id}/transcripts/labeled")
    assert response.status_code == 200
    body = response.json()
    assert "Alex Hormozi:" in body["text"]
    assert "Hello world" in body["text"]


def test_source_segments_endpoint(client):
    source_id = client.test_source_id
    response = client.get(f"/personas/hormozi/sources/{source_id}/segments")
    assert response.status_code == 200
    body = response.json()
    assert len(body["segments"]) == 1
    assert body["segments"][0]["speaker_type"] == "target"


def test_quotes_endpoint(client):
    response = client.get("/personas/hormozi/quotes")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["segment_id"] == "seg-1"
    assert "t=1" in body[0]["source_link"]


def test_unit_detail_endpoint(client):
    unit_id = client.test_unit_id
    response = client.get(f"/personas/hormozi/units/{unit_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["content_type"] == "quote"
    assert len(body["quotes"]) == 1
