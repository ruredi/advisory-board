from __future__ import annotations

import re
from pathlib import Path

from memory_builder.models import Confidence, ContentType, KnowledgeUnit, SourceNature


def parse_visual_description(description: str) -> tuple[list[str], list[str], list[str]]:
    frameworks: list[str] = []
    processes: list[str] = []
    steps: list[str] = []

    for line in description.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        step_match = re.match(r"^(?:\d+[\).\:-]|\-|\*)\s*(.+)$", stripped)
        if step_match:
            steps.append(step_match.group(1).strip())
            continue
        if "framework" in stripped.lower() and ":" in stripped:
            frameworks.append(stripped.split(":", 1)[1].strip())

    if not frameworks and "value equation" in description.lower():
        frameworks.append("Value Equation")
    if not frameworks and "grand slam offer" in description.lower():
        frameworks.append("Grand Slam Offer")

    if steps and not processes:
        processes.append("visual process")

    return frameworks, processes, steps


def visual_assets_to_units(
    *,
    persona_id: str,
    source_id: int,
    source_url: str,
    visual_assets: list[dict],
    source_nature: str = SourceNature.VISUAL,
) -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    for asset in visual_assets:
        description = str(asset.get("description") or "").strip()
        if not description:
            page = asset.get("page")
            description = f"Visual teaching asset on page {page} from {source_url}."
        frameworks, processes, steps = parse_visual_description(description)
        content_type = ContentType.VISUAL_FRAMEWORK
        if steps:
            content_type = ContentType.STEP_BY_STEP
        elif "diagram" in description.lower() or "flowchart" in description.lower():
            content_type = ContentType.DIAGRAM

        units.append(
            KnowledgeUnit(
                persona_id=persona_id,
                source_id=source_id,
                content_type=content_type,
                chunk_text=description[:2000],
                visual_description=description[:2000],
                frameworks=frameworks,
                processes=processes,
                steps=steps,
                confidence=Confidence.MEDIUM if steps or frameworks else Confidence.WEAK,
                source_nature=source_nature,
                evidence_type="source_supported" if asset.get("path") else "inferred_from_sources",
                retrieval_priority=75 if steps else 65,
            )
        )
    return units
