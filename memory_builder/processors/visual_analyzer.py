from __future__ import annotations

import os
from pathlib import Path

from memory_builder.gemini_client import build_gemini_client
from memory_builder.models import ProcessedDocument
from memory_builder.telemetry.context import get_run_context


def describe_visual_asset(image_path: Path, model: str = "gemini-2.5-flash") -> str:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return f"Visual asset at {image_path.name}; enable GOOGLE_API_KEY for detailed diagram analysis."

    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("google-genai package is required for visual analysis") from exc

    client = build_gemini_client(api_key)
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    prompt = (
        "Describe this teaching visual for search indexing. "
        "If it shows a process, framework, table, or diagram, extract numbered steps or components. "
        "Return concise plain text only."
    )
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type=mime),
                ],
            )
        ],
    )
    ctx = get_run_context()
    if ctx:
        ctx.record_gemini(
            response=response,
            operation="vision",
            model=model,
            input_modality="image",
            metadata={"image_file": image_path.name},
        )
    return (response.text or "").strip()


def enrich_document_with_visuals(document: ProcessedDocument, model: str = "gemini-2.5-flash") -> ProcessedDocument:
    descriptions: list[str] = []
    for asset in document.visual_assets:
        image_path = asset.get("path")
        if not image_path:
            descriptions.append(
                f"Page {asset.get('page')}: visual content detected ({asset.get('image_count', 0)} images)."
            )
            continue
        path = Path(image_path)
        if path.exists():
            descriptions.append(describe_visual_asset(path, model=model))
    if descriptions:
        document.visual_assets = [{**asset, "description": descriptions[index] if index < len(descriptions) else ""}
                                   for index, asset in enumerate(document.visual_assets)]
        document.text = document.text + "\n\n## Visual Descriptions\n" + "\n\n".join(descriptions)
    return document
