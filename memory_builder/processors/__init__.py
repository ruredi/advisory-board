from __future__ import annotations

from memory_builder.models import SourceType
from memory_builder.processors.pdf_document import process_pdf
from memory_builder.processors.podcast_transcript import is_podcast_audio_url, process_podcast
from memory_builder.processors.social_post import process_social_post, social_platform
from memory_builder.processors.visual_analyzer import enrich_document_with_visuals
from memory_builder.processors.web_article import process_web_article
from memory_builder.processors.youtube_transcript import process_youtube


def process_source(
    persona_id: str,
    source_type: str,
    source_url: str,
    vision_model: str,
    root=None,
    *,
    transcription_model: str = "gemini-2.5-flash",
    source_title: str = "",
    display_name: str = "",
    speaker_names: list[str] | None = None,
    speaker_labeled_transcription: bool = False,
    allow_unlabeled_fallback: bool = False,
):
    if source_type == SourceType.YOUTUBE:
        document = process_youtube(
            persona_id,
            source_url,
            root,
            transcription_model=transcription_model,
            display_name=display_name,
            speaker_names=speaker_names,
            speaker_labeled_transcription=speaker_labeled_transcription,
            allow_unlabeled_fallback=allow_unlabeled_fallback,
        )
    elif source_type == SourceType.PDF:
        document = process_pdf(persona_id, source_url, root)
    elif source_type == SourceType.SOCIAL and social_platform(source_url):
        document = process_social_post(persona_id, source_url, root)
    elif source_type == SourceType.PODCAST and is_podcast_audio_url(source_url):
        document = process_podcast(
            persona_id,
            source_url,
            root,
            transcription_model=transcription_model,
            title=source_title,
            display_name=display_name,
            speaker_names=speaker_names,
            speaker_labeled_transcription=speaker_labeled_transcription,
        )
    elif source_type in {SourceType.WEB, SourceType.PODCAST}:
        document = process_web_article(persona_id, source_url, root)
    else:
        document = process_web_article(persona_id, source_url, root)
    if document.visual_assets:
        document = enrich_document_with_visuals(document, model=vision_model)
    return document
