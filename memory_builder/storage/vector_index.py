from __future__ import annotations

from pathlib import Path

from memory_builder.storage.embeddings import EmbeddingClient
from memory_builder.storage.qdrant_store import QdrantStore
from memory_builder.storage.sqlite_store import SQLiteStore


class VectorIndex:
    def __init__(
        self,
        store: SQLiteStore,
        model: str = "text-embedding-3-small",
        *,
        root: Path | None = None,
        qdrant_url: str | None = None,
        qdrant_local_path: Path | None = None,
    ) -> None:
        self.store = store
        self.client = EmbeddingClient(model=model)
        self.qdrant = QdrantStore(
            store.persona_id,
            root=root or store.root,
            url=qdrant_url,
            local_path=qdrant_local_path,
        )

    def index_unit(self, unit_id: int, text: str) -> None:
        vector = self.client.embed([text])[0]
        self.qdrant.upsert_unit(unit_id, vector)
        self.store.save_embedding(unit_id, self.client.model, vector)

    def index_missing(self) -> int:
        rows = self.store.connect().execute(
            """
            SELECT k.id, k.chunk_text, k.visual_description, k.frameworks, k.processes, k.steps
            FROM knowledge_units k
            WHERE k.persona_id = ? AND k.is_new_information = 1 AND k.duplicate_of IS NULL
            ORDER BY k.id ASC
            """,
            (self.store.persona_id,),
        ).fetchall()
        count = 0
        for row in rows:
            unit_id = int(row["id"])
            if self.qdrant.has_unit(unit_id):
                continue
            parts = [row["chunk_text"], row["visual_description"]]
            for field in ("frameworks", "processes", "steps"):
                value = row[field]
                if value and value != "[]":
                    parts.append(value)
            text = "\n".join(part for part in parts if part)
            self.index_unit(unit_id, text)
            count += 1
        return count

    def search(self, query: str, top_k: int = 8) -> list[tuple[int, float]]:
        query_vector = self.client.embed([query])[0]
        return self.qdrant.search(query_vector, top_k=top_k)
