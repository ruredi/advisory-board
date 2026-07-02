from __future__ import annotations

from dataclasses import dataclass

from memory_builder.config import load_persona_config
from memory_builder.paths import project_root
from memory_builder.storage.sqlite_store import SQLiteStore
from memory_builder.storage.vector_index import VectorIndex


@dataclass
class RetrievedUnit:
    unit_id: int
    score: float
    chunk_text: str
    content_type: str
    frameworks: list[str]
    processes: list[str]
    steps: list[str]
    quotes: list[dict]
    confidence: str
    source_title: str
    source_url: str
    source_date: str | None
    source_type: str
    channel_url: str | None
    evidence_type: str


class MemorySearch:
    def __init__(self, persona_id: str, root=None, top_k: int = 8) -> None:
        self.root = root or project_root()
        self.persona_id = persona_id
        self.config = load_persona_config(persona_id, self.root)
        self.store = SQLiteStore(persona_id, self.root)
        if self.store.path.exists():
            self.store.connect()
        else:
            self.store.initialize()
        self.vector_index = VectorIndex(
            self.store,
            model=self.config.embedding_model,
            root=self.root,
            qdrant_url=self.config.qdrant_url,
        )
        self.top_k = top_k

    def search(self, query: str) -> list[RetrievedUnit]:
        hits = self.vector_index.search(query, top_k=self.top_k)
        results: list[RetrievedUnit] = []
        conn = self.store.connect()
        for unit_id, score in hits:
            row = conn.execute(
                """
                SELECT k.*, s.source_title, s.source_url, s.source_date, s.source_type, s.channel_url
                FROM knowledge_units k
                JOIN sources s ON s.id = k.source_id
                WHERE k.id = ?
                """,
                (unit_id,),
            ).fetchone()
            if not row:
                continue
            unit = self.store.row_to_knowledge_unit(row)
            results.append(
                RetrievedUnit(
                    unit_id=unit_id,
                    score=score,
                    chunk_text=unit.chunk_text,
                    content_type=unit.content_type,
                    frameworks=unit.frameworks,
                    processes=unit.processes,
                    steps=unit.steps,
                    quotes=unit.quotes,
                    confidence=unit.confidence,
                    source_title=row["source_title"],
                    source_url=row["source_url"],
                    source_date=row["source_date"],
                    source_type=str(row["source_type"] or ""),
                    channel_url=row["channel_url"],
                    evidence_type=unit.evidence_type,
                )
            )
        return results


def build_context_pack(persona_id: str, question: str, root=None, top_k: int = 6) -> str:
    search = MemorySearch(persona_id, root=root, top_k=top_k)
    hits = search.search(question)
    if not hits:
        return "No indexed source-backed memory was retrieved for this question."

    lines = [
        "SOURCE-BACKED MEMORY (use for evidence; do not invent quotes):",
        "",
    ]
    for index, hit in enumerate(hits, start=1):
        lines.append(f"[{index}] {hit.source_title}")
        lines.append(f"URL: {hit.source_url}")
        if hit.source_date:
            lines.append(f"Date: {hit.source_date}")
        lines.append(f"Type: {hit.content_type} | Confidence: {hit.confidence} | Evidence: {hit.evidence_type}")
        if hit.frameworks:
            lines.append("Frameworks: " + ", ".join(hit.frameworks))
        if hit.processes:
            lines.append("Processes: " + ", ".join(hit.processes))
        if hit.steps:
            lines.append("Steps:")
            for step in hit.steps:
                lines.append(f"- {step}")
        if hit.quotes:
            for quote in hit.quotes:
                if quote.get("is_verbatim") and quote.get("text"):
                    lines.append(f'Quote: "{quote["text"]}"')
        lines.append(hit.chunk_text[:1200])
        lines.append("")
    lines.extend(
        [
            "Quote guard:",
            "- Use verbatim quotes only when marked above.",
            "- If evidence is weak, say there is insufficient indexed evidence.",
            "- Do not fabricate book titles, podcast quotes, or process steps.",
        ]
    )
    return "\n".join(lines)
