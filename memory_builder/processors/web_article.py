from __future__ import annotations

from pathlib import Path

import httpx
import trafilatura

from memory_builder.fetch.downloader import fetch_url, save_json_metadata, save_raw_bytes, source_slug
from memory_builder.models import MediaFormat, ProcessedDocument, SourceNature
from memory_builder.paths import sources_processed_dir, sources_raw_dir


def process_web_article(persona_id: str, source_url: str, root: Path | None = None) -> ProcessedDocument:
    from memory_builder.paths import project_root

    base_root = root or project_root()
    content, headers = fetch_url(source_url)
    save_raw_bytes(persona_id, source_url, "page.html", content, base_root)

    extracted = trafilatura.extract(
        content.decode("utf-8", errors="ignore"),
        url=source_url,
        include_comments=False,
        include_tables=True,
        output_format="txt",
    )
    if not extracted:
        raise RuntimeError(f"Could not extract article text from {source_url}")

    metadata = trafilatura.extract_metadata(content.decode("utf-8", errors="ignore"), default_url=source_url)
    title = metadata.title if metadata and metadata.title else source_url
    save_json_metadata(
        persona_id,
        source_url,
        {
            "title": title,
            "author": metadata.author if metadata else None,
            "date": metadata.date if metadata else None,
            "source_url": source_url,
        },
        base_root,
    )

    processed_dir = sources_processed_dir(persona_id, base_root) / source_slug(source_url)
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / "document.txt").write_text(extracted, encoding="utf-8")

    return ProcessedDocument(
        title=title,
        text=extracted,
        source_nature=SourceNature.WRITTEN,
        media_format=MediaFormat.TEXT,
        metadata={"source_url": source_url, "content_type": headers.get("content-type", "")},
    )
