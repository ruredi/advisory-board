from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from memory_builder.paths import memory_dir


class QdrantStore:
    def __init__(
        self,
        persona_id: str,
        *,
        root: Path | None = None,
        url: str | None = None,
        local_path: Path | None = None,
        collection_prefix: str = "persona",
    ) -> None:
        self.persona_id = persona_id
        self.collection_name = f"{collection_prefix}_{persona_id}"
        self.root = root
        self.url = url or os.environ.get("QDRANT_URL", "").strip() or None
        self.local_path = local_path
        self._client = None
        self._dimensions: int | None = None

    def _resolve_local_path(self) -> Path:
        if self.local_path:
            return self.local_path
        base = memory_dir(self.root) / "qdrant"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def client(self):
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("Install qdrant-client: pip install qdrant-client") from exc

        if self.url:
            self._client = QdrantClient(url=self.url)
        else:
            self._client = QdrantClient(path=str(self._resolve_local_path()))
        return self._client

    def ensure_collection(self, dimensions: int) -> None:
        from qdrant_client.http import models as qmodels

        if self._dimensions == dimensions and self.collection_exists():
            return

        client = self.client
        if self.collection_exists():
            info = client.get_collection(self.collection_name)
            current = info.config.params.vectors.size
            if current != dimensions:
                client.delete_collection(self.collection_name)
            else:
                self._dimensions = dimensions
                return

        client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(size=dimensions, distance=qmodels.Distance.COSINE),
        )
        self._dimensions = dimensions

    def collection_exists(self) -> bool:
        client = self.client
        try:
            collections = client.get_collections().collections
        except Exception:
            return False
        return any(item.name == self.collection_name for item in collections)

    def upsert_unit(self, unit_id: int, vector: list[float], payload: dict[str, Any] | None = None) -> None:
        from qdrant_client.http import models as qmodels

        self.ensure_collection(len(vector))
        point_payload = {"persona_id": self.persona_id, "knowledge_unit_id": unit_id}
        if payload:
            point_payload.update(payload)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=unit_id,
                    vector=vector,
                    payload=point_payload,
                )
            ],
        )

    def has_unit(self, unit_id: int) -> bool:
        if not self.collection_exists():
            return False
        records = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[unit_id],
            with_vectors=False,
        )
        return bool(records)

    def delete_units(self, unit_ids: list[int]) -> None:
        if not unit_ids or not self.collection_exists():
            return
        from qdrant_client.http import models as qmodels

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(points=unit_ids),
        )

    def search(self, vector: list[float], top_k: int = 8) -> list[tuple[int, float]]:
        if not self.collection_exists():
            return []
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        results: list[tuple[int, float]] = []
        for hit in response.points:
            unit_id = int(hit.payload.get("knowledge_unit_id", hit.id))
            results.append((unit_id, float(hit.score)))
        return results

    @classmethod
    def memory_client(cls, *, path: str = ":memory:") -> "QdrantStore":
        store = cls("__test__", collection_prefix="test")
        from qdrant_client import QdrantClient

        store._client = QdrantClient(path=path)
        store.collection_name = "test_memory"
        return store
