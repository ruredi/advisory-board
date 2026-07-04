from __future__ import annotations

from memory_builder.paths import project_root

# Advisor ID -> NotebookLM forrás mappa (docs/notebooklm-forrasok/…)
ADVISOR_NOTEBOOKLM_DIRS: dict[str, str] = {
    "hormozi": "alex-hormozi",
    "jobs": "steve-jobs",
    "musk": "elon-musk",
    "buffett": "warren-buffett",
    "bezos": "jeff-bezos",
    "thiel": "peter-thiel",
}

DEFAULT_SOCIAL_PROFILES: dict[str, list[dict[str, str]]] = {
    "hormozi": [
        {"platform": "x", "username": "alexhormozi"},
        {"platform": "instagram", "username": "hormozi"},
    ],
    "musk": [{"platform": "x", "username": "elonmusk"}],
    "thiel": [{"platform": "x", "username": "peterthiel"}],
    "bezos": [{"platform": "x", "username": "JeffBezos"}],
}

DEFAULT_ALLOWED_DOMAINS: dict[str, list[str]] = {
    "hormozi": [
        "acquisition.com",
        "hormozi.blog",
        "youtube.com",
        "youtu.be",
        "podcasts.apple.com",
        "open.spotify.com",
    ],
    "jobs": ["apple.com", "stevejobsarchive.com", "youtube.com", "youtu.be"],
    "musk": ["tesla.com", "spacex.com", "x.com", "twitter.com", "youtube.com", "youtu.be"],
    "buffett": ["berkshirehathaway.com"],
    "bezos": ["amazon.com", "x.com", "twitter.com"],
    "thiel": ["foundersfund.com", "x.com", "twitter.com"],
}

DEFAULT_WATCH_FEEDS: dict[str, list[dict[str, str]]] = {
    "hormozi": [
        {
            "type": "youtube_channel",
            "url": "https://www.youtube.com/@AlexHormozi",
            "label": "Alex Hormozi YouTube",
        },
        {"type": "web", "url": "https://www.acquisition.com/", "label": "Acquisition.com homepage"},
    ],
    "jobs": [
        {"type": "web", "url": "https://stevejobsarchive.com/", "label": "Steve Jobs Archive"},
    ],
    "buffett": [
        {"type": "web", "url": "https://www.berkshirehathaway.com/", "label": "Berkshire Hathaway"},
    ],
}


def default_seed_link_file(advisor_id: str) -> str | None:
    folder = ADVISOR_NOTEBOOKLM_DIRS.get(advisor_id)
    if folder is None:
        return None
    rel = f"docs/notebooklm-forrasok/{folder}/{folder}-linkek.txt"
    if (project_root() / rel).is_file():
        return rel
    return None


def default_source_config(advisor_id: str, display_name: str) -> dict:
    seed_file = default_seed_link_file(advisor_id)
    seed_link_files = [seed_file] if seed_file else []
    return {
        "persona_id": advisor_id,
        "display_name": display_name,
        "seed_link_files": seed_link_files,
        "speaker_names": [display_name],
        "allowed_domains": DEFAULT_ALLOWED_DOMAINS.get(advisor_id, []),
        "watch_feeds": DEFAULT_WATCH_FEEDS.get(advisor_id, []),
        "social_profiles": DEFAULT_SOCIAL_PROFILES.get(advisor_id, []),
        "min_confidence": "weak",
        "embedding_model": "text-embedding-3-small",
        "extraction_model": "gemini-2.5-flash",
        "transcription_model": "gemini-2.5-flash",
        "vision_model": "gemini-2.5-flash",
        "vector_store": "qdrant",
        "qdrant_url": "",
    }
