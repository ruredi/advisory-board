from __future__ import annotations

from pathlib import Path

import fitz

from memory_builder.fetch.downloader import fetch_url, save_json_metadata, save_raw_bytes, source_slug
from memory_builder.models import MediaFormat, ProcessedDocument, SourceNature
from memory_builder.paths import sources_processed_dir


def process_pdf(persona_id: str, source_url: str, root: Path | None = None) -> ProcessedDocument:
    from memory_builder.paths import project_root

    base_root = root or project_root()
    content, _headers = fetch_url(source_url)
    save_raw_bytes(persona_id, source_url, "document.pdf", content, base_root)

    doc = fitz.open(stream=content, filetype="pdf")
    pages: list[str] = []
    visual_assets: list[dict] = []
    raw_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    raw_dir.mkdir(parents=True, exist_ok=True)
    images_dir = raw_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"## Page {index}\n{text}")
        images = page.get_images(full=True)
        for image_index, image in enumerate(images, start=1):
            xref = image[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n >= 5:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                image_path = images_dir / f"page_{index}_img_{image_index}.png"
                pix.save(image_path)
                visual_assets.append(
                    {
                        "page": index,
                        "path": str(image_path),
                        "source_url": source_url,
                    }
                )
            except Exception:
                visual_assets.append(
                    {
                        "page": index,
                        "image_count": 1,
                        "source_url": source_url,
                    }
                )

    full_text = "\n\n".join(pages)
    if not full_text.strip():
        raise RuntimeError(f"No extractable text in PDF {source_url}")

    title = doc.metadata.get("title") or source_url
    save_json_metadata(
        persona_id,
        source_url,
        {"title": title, "page_count": doc.page_count, "source_url": source_url},
        base_root,
    )

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "document.txt").write_text(full_text, encoding="utf-8")

    return ProcessedDocument(
        title=title,
        text=full_text,
        source_nature=SourceNature.WRITTEN,
        media_format=MediaFormat.TEXT,
        metadata={"page_count": doc.page_count, "source_url": source_url},
        visual_assets=visual_assets,
    )
