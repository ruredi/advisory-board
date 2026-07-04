from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from memory_builder.channel_registry import load_channels
from memory_builder.config import load_persona_config
from memory_builder.discovery.profile_urls import (
    canonicalize_profile_url,
    classify_platform,
    profile_identity_key,
)
from memory_builder.discovery.seed_links import (
    classify_source_type,
    infer_source_nature,
    is_processable_source,
    is_social_post_url,
)
from memory_builder.discovery.source_discovery import _matches_persona_identity, _persona_name_tokens
from memory_builder.discovery.youtube_ytdlp import ytdlp_available
from memory_builder.models import SourceRecord, SourceStatus
from memory_builder.paths import project_root
from memory_builder.review.manual_link import parse_manual_review_link
from memory_builder.selected_sources import add_selected_source, platform_for_channel_type
from memory_builder.source_registry import load_approved, username_from_url
from memory_builder.storage.sqlite_store import SQLiteStore, normalize_url
from memory_builder.telemetry.source_labels import platform_label

log = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.72


@dataclass
class LinkMetadata:
    title: str = ""
    channel_url: str | None = None
    source_date: str | None = None


@dataclass
class ResolvedLink:
    url: str
    normalized_url: str
    kind: str  # content | content_channel | social_profile | unsupported
    source_type: str
    platform: str
    title: str
    channel_url: str | None = None
    channel_type: str | None = None
    processable: bool = False
    message: str = ""


@dataclass
class PersonaMatch:
    persona_id: str
    display_name: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    selected: bool = False


@dataclass
class AnalyzeResult:
    resolved: ResolvedLink
    matched_personas: list[PersonaMatch]


@dataclass
class SubmitPersonaResult:
    persona_id: str
    source_id: int | None = None
    channel_id: str | None = None
    status: str = "pending"
    job_id: str | None = None
    message: str = ""


@dataclass
class SubmitResult:
    resolved: ResolvedLink
    results: list[SubmitPersonaResult]


def _normalize_input_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("URL is required")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return normalize_url(cleaned)


def _urls_related(left: str, right: str) -> bool:
    left_norm = normalize_url(left).rstrip("/").lower()
    right_norm = normalize_url(right).rstrip("/").lower()
    if left_norm == right_norm:
        return True
    return left_norm.startswith(right_norm) or right_norm.startswith(left_norm)


def _profile_keys_for_url(url: str) -> set[str]:
    keys: set[str] = set()
    canonical = canonicalize_profile_url(url)
    if canonical:
        key = profile_identity_key(canonical)
        if key:
            keys.add(key)
    username = username_from_url(url)
    platform = classify_platform(url)
    if platform and username:
        if platform == "youtube" and username.startswith("@"):
            keys.add(f"youtube:@{username.lstrip('@').lower()}")
        elif platform == "youtube":
            keys.add(f"youtube:channel:{username}")
        else:
            keys.add(f"{platform}:{username.lower()}")
    return keys


def fetch_link_metadata(url: str, source_type: str) -> LinkMetadata:
    if source_type != "youtube" or not ytdlp_available():
        return LinkMetadata(title=url)
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--no-warnings",
        "--no-update",
        "--print",
        "%(title)s\t%(uploader_url)s\t%(upload_date)s",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("yt-dlp metadata lookup failed for %s: %s", url, exc)
        return LinkMetadata(title=url)
    line = (result.stdout or "").strip().splitlines()[0] if result.stdout else ""
    if not line or result.returncode not in {0, 1}:
        return LinkMetadata(title=url)
    parts = line.split("\t")
    title = parts[0].strip() if parts else url
    channel_url = parts[1].strip() if len(parts) > 1 and parts[1].strip() not in {"", "NA"} else None
    upload_date = parts[2].strip() if len(parts) > 2 else ""
    source_date = None
    if upload_date and upload_date != "NA" and len(upload_date) == 8:
        source_date = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}T00:00:00+00:00"
    return LinkMetadata(title=title or url, channel_url=channel_url, source_date=source_date)


def resolve_submitted_link(url: str, *, metadata: LinkMetadata | None = None) -> ResolvedLink:
    normalized = _normalize_input_url(url)
    manual = parse_manual_review_link(normalized)
    meta = metadata or LinkMetadata()
    source_type = classify_source_type(normalized)

    if manual is not None and manual.kind == "content_channel":
        platform = platform_for_channel_type(manual.channel_type or "web_site")
        return ResolvedLink(
            url=url.strip(),
            normalized_url=manual.url,
            kind="content_channel",
            source_type=source_type,
            platform=platform_label(platform, manual.url),
            title=manual.label or manual.url,
            channel_url=manual.url,
            channel_type=manual.channel_type,
            processable=True,
            message="Content csatorna — regisztrálás után discovery indítható.",
        )

    if is_processable_source(normalized):
        title = meta.title or normalized
        return ResolvedLink(
            url=url.strip(),
            normalized_url=normalized,
            kind="content",
            source_type=source_type,
            platform=platform_label(source_type, normalized, channel_url=meta.channel_url or ""),
            title=title,
            channel_url=meta.channel_url,
            processable=True,
            message="Egyedi tartalom — feldolgozásra vár.",
        )

    if manual is not None and manual.kind == "social":
        return ResolvedLink(
            url=url.strip(),
            normalized_url=manual.url,
            kind="social_profile",
            source_type="social",
            platform=platform_label("social", manual.url),
            title=manual.url,
            processable=True,
            message="Social profil — hozzáadás után timeline discovery futtatható.",
        )

    return ResolvedLink(
        url=url.strip(),
        normalized_url=normalized,
        kind="unsupported",
        source_type=source_type,
        platform=platform_label(source_type, normalized),
        title=normalized,
        processable=False,
        message="Ez a link nem feldolgozható tartalom (profil/home oldal vagy ismeretlen formátum).",
    )


def _score_persona_match(
    persona_id: str,
    *,
    url: str,
    title: str,
    channel_url: str | None,
    source_type: str,
    hint_persona_id: str | None,
    root: Path,
) -> PersonaMatch | None:
    config = load_persona_config(persona_id)
    signals: list[str] = []
    score = 0.0

    if hint_persona_id and persona_id == hint_persona_id:
        signals.append("ui_hint")
        score = max(score, 0.99)

    url_keys = _profile_keys_for_url(url)
    if channel_url:
        url_keys.update(_profile_keys_for_url(channel_url))

    approved = load_approved(persona_id, root)
    if approved:
        for source in approved.sources:
            if source.archived:
                continue
            source_keys = _profile_keys_for_url(source.url)
            if url_keys and source_keys & url_keys:
                signals.append(f"approved:{source.platform}")
                score = max(score, 0.95)
            username = (source.username or username_from_url(source.url)).lower()
            if username and _matches_persona_identity(url, username, config.display_name, config.speaker_names):
                signals.append(f"username:{username}")
                score = max(score, 0.88)

    registry = load_channels(persona_id, root)
    for channel in registry.channels:
        if channel.metadata.get("archived"):
            continue
        if channel_url and _urls_related(channel_url, channel.url):
            signals.append(f"channel:{channel.type}")
            score = max(score, 0.93)
        if _urls_related(url, channel.url):
            signals.append(f"channel_url:{channel.type}")
            score = max(score, 0.90)

    blob = f"{url} {title} {channel_url or ''}"
    tokens = _persona_name_tokens(config.display_name, config.speaker_names)
    matched_tokens = sorted(token for token in tokens if token in blob.lower())
    if matched_tokens:
        signals.append(f"name:{','.join(matched_tokens)}")
        score = max(score, min(0.98, 0.74 + 0.06 * len(matched_tokens)))

    host = urlparse(url).netloc.lower().removeprefix("www.")
    for domain in config.allowed_domains:
        domain = domain.lower().removeprefix("www.")
        if host == domain or host.endswith("." + domain):
            signals.append(f"domain:{domain}")
            score = max(score, 0.82)

    if source_type == "social" and is_social_post_url(url):
        post_username = username_from_url(url)
        if post_username and approved:
            for source in approved.sources:
                if source.archived:
                    continue
                approved_username = (source.username or username_from_url(source.url)).lower()
                if approved_username and approved_username == post_username.lower():
                    signals.append(f"post_author:{approved_username}")
                    score = max(score, 0.96)

    if score < MATCH_THRESHOLD:
        return None
    return PersonaMatch(
        persona_id=persona_id,
        display_name=config.display_name,
        confidence=round(score, 2),
        signals=signals,
        selected=bool(hint_persona_id and persona_id == hint_persona_id) or score >= 0.90,
    )


def match_personas_for_link(
    resolved: ResolvedLink,
    *,
    hint_persona_id: str | None = None,
    persona_ids: list[str] | None = None,
    root: Path | None = None,
) -> list[PersonaMatch]:
    root = root or project_root()
    from api.personas import list_persona_ids

    candidates = persona_ids or list_persona_ids()
    matches: list[PersonaMatch] = []
    for persona_id in candidates:
        match = _score_persona_match(
            persona_id,
            url=resolved.normalized_url,
            title=resolved.title,
            channel_url=resolved.channel_url,
            source_type=resolved.source_type,
            hint_persona_id=hint_persona_id,
            root=root,
        )
        if match is not None:
            matches.append(match)

    matches.sort(key=lambda item: (-item.confidence, item.display_name))
    if hint_persona_id and not any(item.persona_id == hint_persona_id for item in matches):
        config = load_persona_config(hint_persona_id)
        matches.insert(
            0,
            PersonaMatch(
                persona_id=hint_persona_id,
                display_name=config.display_name,
                confidence=0.99,
                signals=["ui_hint"],
                selected=True,
            ),
        )
    elif matches and not any(item.selected for item in matches):
        matches[0].selected = True
    return matches


def analyze_submitted_link(
    url: str,
    *,
    hint_persona_id: str | None = None,
    root: Path | None = None,
) -> AnalyzeResult:
    root = root or project_root()
    normalized = _normalize_input_url(url)
    source_type = classify_source_type(normalized)
    metadata = fetch_link_metadata(normalized, source_type)
    resolved = resolve_submitted_link(url, metadata=metadata)
    if resolved.kind == "content" and metadata.title:
        resolved.title = metadata.title
        if metadata.channel_url:
            resolved.channel_url = metadata.channel_url
    matched = match_personas_for_link(resolved, hint_persona_id=hint_persona_id, root=root)
    return AnalyzeResult(resolved=resolved, matched_personas=matched)


def _register_content(
    persona_id: str,
    resolved: ResolvedLink,
    *,
    root: Path,
) -> tuple[int, str]:
    store = SQLiteStore(persona_id, root)
    store.initialize()
    try:
        existing = store.get_source_by_url(resolved.normalized_url)
        record = SourceRecord(
            persona_id=persona_id,
            source_url=resolved.normalized_url,
            source_title=resolved.title,
            source_type=resolved.source_type,
            source_nature=infer_source_nature(resolved.source_type, resolved.normalized_url),
            status=SourceStatus.PENDING,
            channel_url=resolved.channel_url,
        )
        source_id = store.upsert_source(record)
        if existing is not None and str(existing["status"]) in {
            SourceStatus.INDEXED,
            SourceStatus.PROCESSED,
            SourceStatus.PROCESSING,
        }:
            return int(existing["id"]), "existing"
        return source_id, "pending"
    finally:
        store.close()


def _start_process_job(persona_id: str, source_id: int) -> str:
    from api.jobs import job_manager

    record = job_manager.start(
        persona_id=persona_id,
        script="memory_sync.py",
        args=[
            "--persona",
            persona_id,
            "--skip-discovery",
            "--source-ids",
            str(source_id),
        ],
    )
    return record.job_id


def submit_submitted_link(
    url: str,
    *,
    persona_ids: list[str],
    process: bool = True,
    hint_persona_id: str | None = None,
    root: Path | None = None,
) -> SubmitResult:
    root = root or project_root()
    analysis = analyze_submitted_link(url, hint_persona_id=hint_persona_id, root=root)
    resolved = analysis.resolved
    if not resolved.processable:
        raise ValueError(resolved.message or "Unsupported link")

    if not persona_ids:
        raise ValueError("Legalább egy advisor kell a beküldéshez.")

    results: list[SubmitPersonaResult] = []
    for persona_id in persona_ids:
        persona_id = persona_id.strip().lower()
        if resolved.kind == "content":
            source_id, status = _register_content(persona_id, resolved, root=root)
            job_id = _start_process_job(persona_id, source_id) if process and status == "pending" else None
            results.append(
                SubmitPersonaResult(
                    persona_id=persona_id,
                    source_id=source_id,
                    status=status,
                    job_id=job_id,
                    message="Forrás felvéve" if status == "pending" else "Már szerepel a rendszerben",
                )
            )
            continue

        channel_type = resolved.channel_type or "web_site"
        selected = add_selected_source(
            persona_id,
            channel_type=channel_type,
            url=resolved.normalized_url,
            label=resolved.title,
            root=root,
        )
        job_id = None
        if process:
            from api.jobs import job_manager

            job_record = job_manager.start(
                persona_id=persona_id,
                script="memory_sync.py",
                args=["--persona", persona_id, "--discover-only", "--discovery-limit", "50"],
            )
            job_id = job_record.job_id
        results.append(
            SubmitPersonaResult(
                persona_id=persona_id,
                channel_id=selected.channel_id,
                status="registered",
                job_id=job_id,
                message="Csatorna/profil regisztrálva",
            )
        )

    return SubmitResult(resolved=resolved, results=results)
