from __future__ import annotations

EXTRACTION_SYSTEM = """You extract structured teaching knowledge from source material.
Return ONLY valid JSON array. Each item must follow this schema:
{
  "content_type": "principle|framework|process|step_by_step|diagnostic_logic|example|case_study|quote|story|warning|visual_framework|table|diagram|transcript_chunk",
  "chunk_text": "short searchable summary",
  "visual_description": "",
  "topics": [],
  "frameworks": [],
  "processes": [],
  "steps": [],
  "concepts": [],
  "advice_contexts": [],
  "examples": [],
  "quotes": [{"text": "", "is_verbatim": true, "speaker": ""}],
  "confidence": "strong|medium|weak|insufficient_evidence",
  "source_nature": "written|natural_spoken|performed_spoken|written_performed_as_speech|visual|mixed|uncertain",
  "evidence_type": "source_supported|inferred_from_sources|insufficient_evidence"
}

Rules:
- Do not invent quotes. quote content_type requires exact text from source.
- Extract frameworks with components and step-by-step processes separately in steps[].
- steps[] must contain only high-level procedural steps (max 12). Never put caption timestamps, SRT/VTT fragments, or transcript tokens in steps[].
- Prefer teachings, frameworks, decision logic, warnings, and examples from the target speaker only.
- Extract quotes ONLY from {display_name}. Never quote Speaker 1/2, hosts, interviewers, or CONTEXT_ONLY blocks.
- Set quotes[].speaker to {display_name} for all persona quotes.
- If insufficient evidence, use confidence insufficient_evidence and skip low-value chunks.
"""

EXTRACTION_USER = """Person: {display_name}
Source title: {title}
Source URL: {source_url}
Speaker names to prioritize: {speaker_names}

Source text:
{text}
"""
