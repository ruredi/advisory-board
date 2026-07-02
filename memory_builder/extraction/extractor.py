from __future__ import annotations

import json
import os
import re
from typing import Any

from memory_builder.extraction.prompts import EXTRACTION_SYSTEM, EXTRACTION_USER
from memory_builder.gemini_client import build_gemini_client
from memory_builder.models import Confidence, ContentType, KnowledgeUnit, SourceNature
from memory_builder.normalize import normalize_string_list
from memory_builder.telemetry.context import get_run_context


def extract_knowledge_units(
    *,
    persona_id: str,
    source_id: int,
    display_name: str,
    speaker_names: list[str],
    title: str,
    source_url: str,
    text: str,
    source_nature: str,
    model: str = "gemini-2.5-flash",
    source_index: int | None = None,
    source_total: int | None = None,
) -> list[KnowledgeUnit]:
    text = text.strip()
    if not text:
        return []
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            return _extract_with_gemini(
                persona_id=persona_id,
                source_id=source_id,
                display_name=display_name,
                speaker_names=speaker_names,
                title=title,
                source_url=source_url,
                text=text,
                source_nature=source_nature,
                model=model,
                api_key=api_key,
                source_index=source_index,
                source_total=source_total,
            )
        except Exception:
            pass
    return _extract_heuristic(
        persona_id=persona_id,
        source_id=source_id,
        display_name=display_name,
        text=text,
        source_nature=source_nature,
    )


def _extract_with_gemini(
    *,
    persona_id: str,
    source_id: int,
    display_name: str,
    speaker_names: list[str],
    title: str,
    source_url: str,
    text: str,
    source_nature: str,
    model: str,
    api_key: str,
    source_index: int | None = None,
    source_total: int | None = None,
) -> list[KnowledgeUnit]:
    client = build_gemini_client(api_key)
    chunks = _chunk_text(text, max_chars=12000)
    chunk_total = len(chunks)
    units: list[KnowledgeUnit] = []
    for chunk_index, chunk in enumerate(chunks, start=1):
        _report_extract_chunk_progress(
            chunk_index=chunk_index,
            chunk_total=chunk_total,
            model=model,
            source_id=source_id,
            source_index=source_index,
            source_total=source_total,
        )
        prompt = EXTRACTION_USER.format(
            display_name=display_name,
            title=title,
            source_url=source_url,
            speaker_names=", ".join(speaker_names),
            text=chunk,
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"system_instruction": EXTRACTION_SYSTEM, "response_mime_type": "application/json"},
        )
        ctx = get_run_context()
        if ctx:
            ctx.record_gemini(
                response=response,
                operation="extraction",
                model=model,
                source_id=source_id,
                metadata={"chunk_chars": len(chunk)},
            )
        payload = _parse_json_array(response.text or "[]")
        units.extend(
            _payload_to_units(
                payload,
                persona_id=persona_id,
                source_id=source_id,
                default_source_nature=source_nature,
            )
        )
    return units


def _report_extract_chunk_progress(
    *,
    chunk_index: int,
    chunk_total: int,
    model: str,
    source_id: int,
    source_index: int | None,
    source_total: int | None,
) -> None:
    prefix = ""
    if source_index is not None and source_total is not None:
        prefix = f"[{source_index}/{source_total}] "
    print(f"{prefix}extract chunk {chunk_index}/{chunk_total} ({model})", flush=True)
    ctx = get_run_context()
    if ctx:
        ctx.event(
            "source_extract",
            f"Extracting chunk {chunk_index}/{chunk_total}",
            source_id=source_id,
            metadata={"chunk_index": chunk_index, "chunk_total": chunk_total},
        )


def _extract_heuristic(
    *,
    persona_id: str,
    source_id: int,
    display_name: str,
    text: str,
    source_nature: str,
) -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    for paragraph in paragraphs[:200]:
        lowered = paragraph.lower()
        content_type = ContentType.TRANSCRIPT_CHUNK
        frameworks: list[str] = []
        processes: list[str] = []
        steps: list[str] = []
        quotes: list[dict[str, Any]] = []
        confidence = Confidence.MEDIUM

        if "value equation" in lowered:
            content_type = ContentType.FRAMEWORK
            frameworks.append("Value Equation")
        elif "grand slam offer" in lowered:
            content_type = ContentType.FRAMEWORK
            frameworks.append("Grand Slam Offer")
        elif re.search(r"\b(step \d+|first,|second,|third,)\b", lowered):
            content_type = ContentType.STEP_BY_STEP
            steps = re.findall(r"(?:Step \d+[:.]?\s*[^\n.]+|\d+\.\s*[^\n.]+)", paragraph, flags=re.IGNORECASE)
        elif '"' in paragraph or "“" in paragraph:
            content_type = ContentType.QUOTE
            match = re.search(r'"([^"]{12,300})"|“([^”]{12,300})”', paragraph)
            if match:
                quote_text = match.group(1) or match.group(2) or ""
                quotes.append({"text": quote_text, "is_verbatim": True, "speaker": display_name})
            else:
                confidence = Confidence.WEAK
        elif any(token in lowered for token in ("framework", "process", "model")):
            content_type = ContentType.FRAMEWORK
        elif any(token in lowered for token in ("avoid", "mistake", "don't", "never")):
            content_type = ContentType.WARNING
        elif any(token in lowered for token in ("for example", "case study", "client")):
            content_type = ContentType.EXAMPLE

        if len(paragraph) < 80 and content_type == ContentType.TRANSCRIPT_CHUNK:
            continue

        units.append(
            KnowledgeUnit(
                persona_id=persona_id,
                source_id=source_id,
                content_type=content_type,
                chunk_text=paragraph[:2000],
                frameworks=frameworks,
                processes=processes,
                steps=steps,
                quotes=quotes,
                confidence=confidence,
                source_nature=source_nature,
                evidence_type="source_supported" if quotes else "inferred_from_sources",
                retrieval_priority=70 if content_type in {ContentType.FRAMEWORK, ContentType.PROCESS, ContentType.STEP_BY_STEP} else 50,
            )
        )
    return units


def _payload_to_units(
    payload: list[dict[str, Any]],
    *,
    persona_id: str,
    source_id: int,
    default_source_nature: str,
) -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        chunk_text = str(item.get("chunk_text", "")).strip()
        if not chunk_text:
            continue
        content_type = str(item.get("content_type", ContentType.TRANSCRIPT_CHUNK))
        quotes = item.get("quotes") or []
        evidence_type = str(item.get("evidence_type", "source_supported"))
        if content_type == ContentType.QUOTE:
            if not quotes or not any(q.get("is_verbatim") and q.get("text") for q in quotes):
                evidence_type = "insufficient_evidence"
                continue
        units.append(
            KnowledgeUnit(
                persona_id=persona_id,
                source_id=source_id,
                content_type=content_type,
                chunk_text=chunk_text,
                visual_description=str(item.get("visual_description", "")),
                topics=normalize_string_list(item.get("topics")),
                frameworks=normalize_string_list(item.get("frameworks")),
                processes=normalize_string_list(item.get("processes")),
                steps=normalize_string_list(item.get("steps")),
                concepts=normalize_string_list(item.get("concepts")),
                advice_contexts=normalize_string_list(item.get("advice_contexts")),
                examples=normalize_string_list(item.get("examples")),
                quotes=list(quotes),
                confidence=str(item.get("confidence", Confidence.MEDIUM)),
                source_nature=str(item.get("source_nature", default_source_nature)),
                evidence_type=evidence_type,
                retrieval_priority=80 if item.get("steps") else 60,
            )
        )
    return units


def _chunk_text(text: str, max_chars: int = 12000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in text.split("\n\n"):
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                size = 0
            chunks.extend(_split_oversized_text(paragraph, max_chars))
            continue
        added = len(paragraph) + (2 if current else 0)
        if size + added > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            size = len(paragraph)
        else:
            current.append(paragraph)
            size += added
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _split_oversized_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    if "\n" in text:
        chunks: list[str] = []
        current: list[str] = []
        size = 0
        for line in text.split("\n"):
            if len(line) > max_chars:
                if current:
                    chunks.append("\n".join(current))
                    current = []
                    size = 0
                chunks.extend(_hard_split(line, max_chars))
                continue
            added = len(line) + (1 if current else 0)
            if size + added > max_chars and current:
                chunks.append("\n".join(current))
                current = [line]
                size = len(line)
            else:
                current.append(line)
                size += added
        if current:
            chunks.append("\n".join(current))
        return chunks
    return _hard_split(text, max_chars)


def _hard_split(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            break_at = text.rfind(" ", start, end)
            if break_at > start + max_chars // 2:
                end = break_at
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end if end > start else start + max_chars
        while start < len(text) and text[start].isspace():
            start += 1
    return chunks


def _parse_json_array(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return list(data["items"])
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[\s*\{.*\}\s*\]", raw, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return []
