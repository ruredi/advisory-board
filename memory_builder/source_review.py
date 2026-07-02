from __future__ import annotations

from datetime import datetime, timezone

from memory_builder.discovery.source_discovery import _candidate_from_url, classify_platform
from memory_builder.source_registry import (
    ApprovedSources,
    SourceCandidate,
    approved_scraper_profiles,
    approved_to_social_profiles,
    load_approved,
    load_candidates,
    save_approved,
    save_candidates,
)
from memory_builder.config import load_persona_config
from memory_builder.discovery.source_discovery import discover_persona_source_candidates
from memory_builder.review.manual_link import parse_manual_review_link, register_manual_content_channel


def run_discovery(persona_id: str, root=None) -> list[SourceCandidate]:
    candidates = discover_persona_source_candidates(persona_id, root)
    save_candidates(persona_id, candidates, root)
    return candidates


def format_candidate_line(index: int, candidate: SourceCandidate) -> str:
    return (
        f"  [{index}] {candidate.url}\n"
        f"       confidence: {candidate.confidence:.2f}  source: {candidate.discovery_source}"
    )


def parse_reject_indices(raw: str, max_index: int) -> set[int]:
    if not raw.strip():
        return set()
    indices: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value < 1 or value > max_index:
            raise ValueError(f"Invalid index: {value}")
        indices.add(value)
    return indices


def apply_review(
    candidates: list[SourceCandidate],
    rejected_indices: set[int],
    manual_urls: list[str],
    persona_id: str,
    reviewed_by: str,
    root=None,
) -> ApprovedSources:
    config = load_persona_config(persona_id, root)
    approved: list[SourceCandidate] = []
    for index, candidate in enumerate(candidates, start=1):
        if index in rejected_indices:
            candidate.status = "rejected"
            continue
        candidate.status = "approved"
        approved.append(candidate)

    for url in manual_urls:
        manual = _candidate_from_url(
            url,
            "manual",
            config.allowed_domains,
            display_name=config.display_name,
            speaker_names=config.speaker_names,
        )
        if manual is None:
            raise ValueError(f"Not a supported profile URL: {url}")
        manual.status = "approved"
        manual.confidence = 1.0
        manual.signals.append("user_submitted")
        if not any(item.url == manual.url for item in approved):
            approved.append(manual)

    approved.sort(key=lambda item: (-item.confidence, item.url))
    return ApprovedSources(
        persona_id=persona_id,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        reviewed_by=reviewed_by,
        sources=approved,
    )


def interactive_review(persona_id: str, reviewed_by: str = "terminal", root=None) -> ApprovedSources:
    candidates = load_candidates(persona_id, root)
    if not candidates:
        candidates = run_discovery(persona_id, root)

    print(f"\n=== Source review: {persona_id} ===\n")
    print("Candidates (open links in browser, then mark NOT theirs):\n")
    for index, candidate in enumerate(candidates, start=1):
        print(format_candidate_line(index, candidate))
        print()

    while True:
        raw = input("Reject which? (e.g. 4,7 or Enter=none): ").strip()
        try:
            rejected = parse_reject_indices(raw, len(candidates))
            break
        except ValueError as exc:
            print(f"Invalid input: {exc}")

    manual_urls: list[str] = []
    while True:
        answer = input("\nVan még oldal amit kihagytunk? [y/N]: ").strip().lower()
        if answer in {"", "n", "no"}:
            break
        if answer not in {"y", "yes"}:
            print("Answer y or n.")
            continue
        link = input("Link: ").strip()
        if not link:
            print("Empty link, skipping.")
            continue
        parsed = parse_manual_review_link(link)
        if parsed is None:
            print("Unsupported URL. Use a social profile (X, Instagram, Facebook, LinkedIn) or a content channel.")
            print("Content channels (YouTube, Spotify, Apple Podcasts): they are added via add_channel.py, not profile review.")
            print("  python3 scripts/add_channel.py --persona", persona_id, "--type spotify_show --url \"...\"")
            continue
        if parsed.kind == "content_channel":
            channel_id = register_manual_content_channel(persona_id, parsed, root=root)
            print(f"Content channel registered: {channel_id}")
            print("Episodes are discovered via memory_sync / add_channel.py --sync (not profile review).")
            continue
        manual_urls.append(parsed.url)
        print(f"Added manual social profile ({classify_platform(parsed.url)}).")

    approved = apply_review(candidates, rejected, manual_urls, persona_id, reviewed_by, root)
    path = save_approved(approved, root)

    print(f"\nApproved: {len(approved.sources)}  |  Rejected: {len(rejected)}")
    print(f"Saved: {path}")
    return approved


def print_approved_summary(persona_id: str, root=None) -> None:
    approved = load_approved(persona_id, root)
    if approved is None:
        raise ValueError(f"No approved sources for {persona_id}")
    print(f"\n=== Approved profile sources: {persona_id} ===\n")
    for source in approved.sources:
        print(f"  [{source.platform}] {source.url}")
        print(f"       confidence: {source.confidence:.2f}  source: {source.discovery_source}")
    scraper_profiles = approved_scraper_profiles(approved)
    all_social = approved_to_social_profiles(approved)
    has_instagram = any(profile["platform"] == "instagram" for profile in all_social)
    skipped_facebook = [
        profile
        for profile in all_social
        if profile["platform"] == "facebook" and has_instagram
    ]
    print(f"\nApproved profiles: {len(approved.sources)}")
    print(f"Social timeline discovery will use {len(scraper_profiles)} scraper profile(s):")
    for profile in scraper_profiles:
        label = profile["platform"]
        if label == "facebook":
            kind = profile.get("facebook_kind", "page")
            print(f"  - {label} ({kind}): {profile['url']}")
        else:
            print(f"  - {label}: @{profile['username']}")
    if skipped_facebook:
        print("Skipped Facebook (Instagram also approved — redundant content):")
        for profile in skipped_facebook:
            print(f"  - {profile['url']}")
    pending = [
        profile
        for profile in all_social
        if profile["platform"] not in {"x", "twitter", "instagram", "tiktok", "threads", "facebook"}
    ]
    if pending:
        print(f"Recorded for later (no scraper yet): {len(pending)}")
        for profile in pending:
            print(f"  - {profile['platform']}: @{profile['username']}")
    print("\nProfile validation complete.")


def submit_review(
    persona_id: str,
    *,
    rejected_indices: set[int] | None = None,
    manual_urls: list[str] | None = None,
    reviewed_by: str = "dashboard",
    root=None,
) -> ApprovedSources:
    """Non-interactive review wrapper for dashboard/API use."""
    candidates = load_candidates(persona_id, root)
    if not candidates:
        candidates = run_discovery(persona_id, root)
    approved = apply_review(
        candidates,
        rejected_indices or set(),
        manual_urls or [],
        persona_id,
        reviewed_by,
        root,
    )
    save_approved(approved, root)
    return approved
