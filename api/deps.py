from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from api.personas import ensure_persona_ready
from memory_builder.env import load_project_env
from memory_builder.storage.sqlite_store import SQLiteStore

load_project_env()


def ensure_persona(persona_id: str) -> None:
    ensure_persona_ready(persona_id)


@contextmanager
def persona_store(persona_id: str) -> Generator[SQLiteStore, None, None]:
    ensure_persona(persona_id)
    store = SQLiteStore(persona_id)
    store.initialize()
    try:
        yield store
    finally:
        store.close()
