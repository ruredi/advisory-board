# Memory System

Operates the continuous source-based knowledge layer for Hermes personas (03 Clone the Memory).

## Scope

- Persona-agnostic builder under `memory_builder/`
- Pilot persona: `hormozi`
- External maintainer workflow only; advisors do not self-modify memory
- Voice and doctrine files are **not** auto-rewritten from memory updates

## Layout

```txt
memory_builder/              # pipeline code
memory/{persona}.sqlite      # metadata: sources, knowledge units, sync log
memory/qdrant/               # embedded local Qdrant storage (default)
memory/qdrant-server/        # docker volume when using docker compose
sources/raw/{persona}/       # fetched originals (transcripts, HTML, social JSON)
sources/processed/{persona}/ # normalized text for extraction
sources/candidates/{persona}.json   # discovered social profile URL candidates
sources/approved/{persona}.yaml     # human-reviewed official profile URLs
sources/channels/{persona}.yaml     # YouTube / podcast / Spotify channel registry
docker-compose.yml           # optional Qdrant server mode

scripts/memory_build.py      # initial build + gate
scripts/memory_sync.py       # daily sync
scripts/memory_search.py     # retrieval debug
scripts/discover_sources.py  # optional: preview social profile candidates
scripts/review_sources.py    # required: interactive profile review
scripts/add_channel.py       # add YouTube / Spotify / podcast channel
scripts/test_scrapfly_api.py # Scrapfly connectivity smoke test
```

## Storage architecture

Two-store setup:

| Store | Role |
|---|---|
| **SQLite** (`memory/{persona}.sqlite`) | Sources, knowledge unit metadata, extraction fields, sync runs |
| **Qdrant** | Vector embeddings + fast similarity search |

SQLite keeps the human-readable teaching graph. Qdrant keeps embeddings for retrieval speed.

Collection naming: `persona_{persona_id}` (example: `persona_hormozi`).

### Qdrant modes

**A) Embedded local (default, no Docker)**

Vectors persist under `memory/qdrant/`. Nothing else to start.

```bash
python3 scripts/memory_build.py --persona hormozi --limit 10
```

**B) Qdrant server via Docker (recommended for heavier builds / concurrent access)**

```bash
docker compose up -d qdrant
export QDRANT_URL=http://localhost:6333
python3 scripts/memory_build.py --persona hormozi
```

Or set in `memory_builder/config/personas/hormozi.yaml`:

```yaml
qdrant_url: http://localhost:6333
```

Embedded mode uses a file lock — run only one build/sync process at a time against `memory/qdrant/`. Server mode avoids that limitation.

## Setup

```bash
cd /Users/andraspolgar/Developer/advisory-board
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PATH="$HOME/Library/Python/3.9/bin:$PATH"  # yt-dlp, if installed via pip --user
```

Optional API keys:

- `OPENAI_API_KEY` — embeddings (`text-embedding-3-small`)
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` — Gemini (`gemini-2.5-flash`: extraction, podcast transcription, PDF vision)
- `SCRAPFLY_KEY` — X/Instagram/Facebook social post scraping (required for social sources)

Without API keys, the builder falls back to deterministic local embeddings and heuristic extraction.

External tools:

- `yt-dlp` — YouTube metadata and transcripts

## Profile source review (required before build)

Official social/profile sources must be discovered and reviewed before `memory_build` or `memory_sync` runs.

**Minimum flow (one command):**

```bash
python3 scripts/review_sources.py --persona hormozi
```

`review_sources.py` runs discovery automatically if `sources/candidates/{persona}.json` does not exist yet.

**Optional preview** (inspect candidates before interactive review):

```bash
python3 scripts/discover_sources.py --persona hormozi
python3 scripts/review_sources.py --persona hormozi
```

Review flow:

1. List of candidate links with **confidence** and **discovery source** (`official_site`, `seed_file`, `persona_config`, `watch_feed`)
2. Mark which are **NOT** theirs (reject by number)
3. `Van még oldal amit kihagytunk? [y/N]` — add manual URLs until `N`
   - **Social profiles** (X, Instagram, LinkedIn, Facebook) → go into `sources/approved/`
   - **Content channels** (YouTube channel, Spotify show, Apple Podcasts) → registered in `sources/channels/` via the same prompt (tracking query params like `?si=...` are stripped). Episodes are synced later with `memory_sync` / `add_channel.py --sync`, not during profile review.

Output: `sources/approved/{persona}.yaml` — only approved profiles are used for social timeline discovery. The legacy `social_profiles` block in persona YAML is a fallback only when no approved file exists.

After review, verify and stop before content discovery:

```bash
python3 scripts/memory_build.py --persona hormozi --profiles-only
```

When ready for content source discovery (still no processing):

```bash
python3 scripts/memory_build.py --persona hormozi --dry-run
```

`memory_build` / `memory_sync` stop with exit code `2` until review is complete.

Emergency bypass (not recommended): `--skip-source-review`

## Content channels (YouTube, Spotify, podcast RSS)

**Source of truth:** `sources/channels/{persona}.yaml`

On first run, channels are bootstrapped from `watch_feeds` in `memory_builder/config/personas/{persona}.yaml`. After that, prefer `add_channel.py` — editing persona YAML `watch_feeds` alone does not add new channels unless you delete the channels file to re-bootstrap.

### Channel types

| `type` | URL example | Discovery |
|---|---|---|
| `youtube_channel` | `https://www.youtube.com/@AlexHormozi` | Channel page → YouTube RSS |
| `spotify_show` | `https://open.spotify.com/show/...` | Resolves Apple Podcasts RSS via iTunes lookup (Spotify is DRM — no direct scrape) |
| `apple_podcast` | `https://podcasts.apple.com/.../id1254720112` | iTunes lookup → RSS |
| `podcast_rss` | `https://rss.example.com/feed.xml` | Direct RSS via feedparser |

### Add a channel

```bash
# YouTube channel — discover + process immediately
python3 scripts/add_channel.py --persona hormozi \
  --type youtube_channel --url "https://www.youtube.com/@AlexHormozi" --sync

# Spotify show (RSS resolved automatically)
python3 scripts/add_channel.py --persona hormozi \
  --type spotify_show --url "https://open.spotify.com/show/6YNopzKDGDwf0auIpPTIID" \
  --label "The Game with Alex Hormozi" --sync

# Apple Podcasts show
python3 scripts/add_channel.py --persona hormozi \
  --type apple_podcast \
  --url "https://podcasts.apple.com/us/podcast/the-game-with-alex-hormozi/id1254720112" \
  --sync

# Raw RSS feed (override or direct)
python3 scripts/add_channel.py --persona hormozi \
  --type podcast_rss --url "https://rss2.flightcast.com/zz5nwp81tktx53wb8fw6qq7j.xml" \
  --rss-url "https://rss2.flightcast.com/zz5nwp81tktx53wb8fw6qq7j.xml" --sync
```

Flags:

- `--sync` — discover new episodes from this channel and process pending sources immediately
- `--limit N` — cap how many sources are processed in the same run
- `--rss-url` — optional RSS override (useful when auto-resolution fails)
- `--label` — human label; also helps Spotify → Apple Podcasts matching

### Processing order

1. **YouTube always first** (`source_type` priority)
2. Podcast / Spotify episodes second
3. Within each type: newest `source_date` first

### YouTube-first title dedup (podcasts)

Cross-platform dedup so the same episode is not processed twice as YouTube + podcast audio:

- Episode numbers stripped from titles (`| Ep 984`, `Episode 12`, …)
- Fuzzy containment match against **indexed** YouTube `source_title` values
- Runs at **discovery** (when DB is available) and again at **process** time
- Match → `status=skipped`, `error_message` points to the YouTube URL

### Resume / cursors

Each channel in `sources/channels/{persona}.yaml` stores:

- `latest_published_at` — watermark; sync only ingests RSS items **newer** than this
- `last_discovered_at` — last time discovery ran for this channel
- `rss_url` — resolved feed URL (filled automatically for Spotify/Apple)

Per-source dates in SQLite:

- `sources.source_date` — RSS `pubDate` or YouTube `upload_date` (YYYYMMDD from yt-dlp)
- `sources.normalized_title` — dedup-normalized title
- `sources.channel_url` — which channel discovered this source

### Podcast processing

Discovery, dedup, and date tracking work for podcast RSS / Spotify shows. **Audio episodes** (`*.mp3` enclosures, Flightcast URLs) are transcribed via **Gemini** (`GOOGLE_API_KEY` / `GEMINI_API_KEY`) into `transcript.txt` + `document.txt`.

Apple Podcasts episode **pages** (HTML) still use `process_web_article()` when the source URL is not a direct audio file.

Smoke test:

```bash
# Quick smoke (first 45s only; needs ffmpeg)
python3 scripts/test_podcast_transcript.py --persona hormozi --clip-seconds 45

# Full latest episode from RSS (slow; uses persona transcription_model, default gemini-2.5-flash)
python3 scripts/test_podcast_transcript.py --persona hormozi
```

YouTube remains preferred when the same episode exists on both platforms (title dedup).

## Social media (Scrapfly)

X, Instagram, and Facebook posts are scraped via [Scrapfly](https://scrapfly.io/), using the same approach as `secret-project/scrapfly-scrapers` (`twitter-scraper`, `instagram-scraper`, plus a custom Facebook module).

Set your API key in `advisory-board/.env` (see `.env.example`), or rely on automatic fallback from `../secret-project/.env`:

```bash
cp .env.example .env
# SCRAPFLY_KEY=...   # or leave empty if secret-project/.env exists
python3 scripts/test_scrapfly_api.py
```

Manual export also works:

```bash
export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
```

Configure fallback social profiles in `memory_builder/config/personas/{persona}.yaml` (used only when `sources/approved/{persona}.yaml` is missing):

```yaml
social_profiles:
  - platform: x
    username: alexhormozi
    max_posts: 50
  - platform: instagram
    username: hormozi
    max_posts: 50
```

Discovery behavior:

| URL type | Seed file | Profile watch |
|---|---|---|
| X/Instagram **post** (`/status/`, `/p/`) | Processed directly | Also discovered from profile timeline |
| X/Instagram **profile** | Skipped in seed (use approved sources) | Scraped via Scrapfly timeline |
| Facebook **post** (`/posts/`, `/reel/`, group post) | Processed directly | Also discovered from page/group timeline |
| Facebook **page** (personal or business) | Skipped in seed (use approved sources) | Scraped via Scrapfly timeline |
| Facebook **group** (`/groups/{name}/`) | Skipped in seed — add manually in review if needed | Only **group-authored** posts (not member posts) |
| Thread Reader thread | Treated as web article | — |

`--only` and social discovery:

- `--only` limits **Scrapfly profile timeline scraping** to the matching platform (`x`, `instagram`, …). Other approved profiles are skipped for that run — avoids burning Scrapfly quota on X when you only want new Instagram posts.
- Seed links and content channels (YouTube / podcast RSS) are **not** filtered by `--only`; they always run unless you pass `--skip-discovery`.
- `--only` also filters **processing** and `--retry-failed` reset to the same platform.

Examples:

```bash
# Refresh Instagram posts only (Scrapfly + process), leave YouTube/RSS discovery unchanged
python3 scripts/memory_build.py --persona hormozi --only instagram

# Process pending Instagram sources without any discovery
python3 scripts/memory_build.py --persona hormozi --only instagram --skip-discovery
```

Facebook selection rule (after profile review):

- If **Instagram is approved** for a persona → Facebook timeline scraping is **skipped** (redundant content).
- If **no Instagram** but Facebook page/group is approved → Facebook scraping runs.
- Public **groups** can be added in review (`Van még oldal?` → paste `https://www.facebook.com/groups/...`). Only posts where the actor is the Group/Page are ingested.

Supported Facebook targets: personal page, business page, public group.

X.com note (2026): GraphQL XHR interception often returns empty without login. The scraper falls back to:

- **Tweet pages** — `og:description` / `og:title` meta tags from rendered HTML
- **Quote tweets** — detects embedded `/user/status/{id}` links on the page, extracts quoted text inline, and fetches the quoted post if truncated
- **Profile timeline** — `/status/{id}` links extracted from rendered profile HTML (typically ~10–15 recent posts without login)

Facebook note: public visibility varies. Personal pages may expose reels/posts in embedded JSON; groups and some business pages may return little without login. The scraper uses rendered HTML + JSON script tags (`post_id`, `message`, `wwwURL`) and `og:description` on individual post pages.

Raw social JSON is saved under `sources/raw/{persona}/`. Processed text goes to `sources/processed/{persona}/`.

Verify Scrapfly connectivity before a build:

```bash
python3 scripts/test_scrapfly_api.py          # Instagram + X tweet + profile discovery
python3 scripts/test_scrapfly_api.py --all    # same (explicit)
python3 scripts/test_scrapfly_api.py --platform instagram
```

Optional live unittest (not run in default CI):

```bash
SCRAPFLY_LIVE_TEST=1 python3 -m unittest tests.test_scrapfly_api_live -v
```

## Commands

### Onboarding (new persona)

```bash
# 1. Review official social profiles (required)
python3 scripts/review_sources.py --persona hormozi

# 2. Verify profiles, stop before content crawl
python3 scripts/memory_build.py --persona hormozi --profiles-only

# 3. Add content channels
python3 scripts/add_channel.py --persona hormozi --type youtube_channel \
  --url "https://www.youtube.com/@AlexHormozi"
python3 scripts/add_channel.py --persona hormozi --type spotify_show \
  --url "https://open.spotify.com/show/6YNopzKDGDwf0auIpPTIID" \
  --label "The Game with Alex Hormozi"
```

### Build and sync

```bash
python3 scripts/memory_build.py --persona hormozi
python3 scripts/memory_build.py --persona hormozi --limit 5
python3 scripts/memory_build.py --persona hormozi --dry-run          # discover only
python3 scripts/memory_build.py --persona hormozi --profiles-only    # gate + approved profiles
python3 scripts/memory_build.py --persona hormozi --skip-source-review  # emergency only
python3 scripts/memory_build.py --persona hormozi --retry-failed     # reset failed → pending, reprocess

# Platform filter: limits social Scrapfly discovery + processing (+ retry-failed reset)
python3 scripts/memory_build.py --persona hormozi --only instagram
python3 scripts/memory_build.py --persona hormozi --only x

# Parallel workers (after a full discovery run): one platform per terminal, skip discovery
python3 scripts/memory_build.py --persona hormozi --only youtube --skip-discovery --retry-failed
python3 scripts/memory_build.py --persona hormozi --only spotify --skip-discovery --retry-failed
python3 scripts/memory_build.py --persona hormozi --only x --skip-discovery --retry-failed
python3 scripts/memory_build.py --persona hormozi --only instagram --skip-discovery --retry-failed

python3 scripts/memory_sync.py --persona hormozi
python3 scripts/memory_sync.py --persona hormozi --limit 10
python3 scripts/memory_sync.py --persona hormozi --only youtube --skip-discovery
python3 scripts/memory_sync.py --persona hormozi --only instagram   # Instagram Scrapfly only
```

### Channels

```bash
python3 scripts/add_channel.py --persona hormozi --type youtube_channel \
  --url "https://www.youtube.com/@AlexHormozi" --sync
```

### Search / debug retrieval

```bash
python3 scripts/memory_search.py hormozi "weak offer diagnosis"
python3 scripts/memory_search.py hormozi "Value Equation steps" --context-pack
```

Advisor runtime with memory:

```bash
python3 scripts/ask_advisor.py hormozi "How would you diagnose a weak offer?" --mode research_grounded --dry-run
```

## Source discovery

Discovery combines several registries:

| Registry | Path | Purpose |
|---|---|---|
| Persona config | `memory_builder/config/personas/{persona}.yaml` | Seed files, allowed domains, fallback `social_profiles` |
| Approved profiles | `sources/approved/{persona}.yaml` | Official X/Instagram/Facebook/… profiles (required before build) |
| Content channels | `sources/channels/{persona}.yaml` | YouTube + podcast/Spotify feeds with resume cursors |
| Seed links | `docs/notebooklm-forrasok/` | Curated article/interview/book URLs |

### Discovery order (each build/sync)

1. Seed link files → individual article/video URLs
2. Content channels (YouTube channels first, then podcast/Spotify RSS)
3. Approved social profiles → X/Instagram/Facebook post timelines (Scrapfly)

### Platform filter (`--only`)

| Stage | Filtered by `--only`? |
|---|---|
| Seed links | No (always runs) |
| Content channels (YouTube / podcast RSS) | No (always runs) |
| Social profile timelines (Scrapfly) | **Yes** — only matching platform |
| Pending/failed processing | **Yes** |
| `--retry-failed` reset | **Yes** |

Supported values: `youtube`, `spotify`, `x`, `instagram`, `web`. Use `--skip-discovery` to skip stages 1–3 entirely and only process existing DB rows.

Implementation: `memory_builder/pipeline/platform_filter.py` (`social_profile_matches_filter`, `platform_sql_filter`).

### Source types

| Source type | How it is discovered | Examples |
|---|---|---|
| `youtube` | Channel RSS via `sources/channels/` | `@AlexHormozi` uploads |
| `podcast` | Podcast RSS (Spotify show → Apple RSS, or direct RSS) | Flightcast MP3 enclosures |
| Seed links | Curated URL lists | interviews, books, articles |
| `web` / `pdf` | Seed URLs or official site crawl | `acquisition.com` essays |
| `social` | Approved profile timelines (Scrapfly) | X posts, Instagram reels |

Discovery intentionally filters out:

- profile/home pages without teaching content
- pure social profile URLs in seed files (use approved profiles + channels instead)
- duplicate canonical URLs
- podcast episodes that match an already-indexed YouTube title (`status=skipped`)

New URLs are upserted into `sources` with `status=pending` (or `skipped` when YouTube dedup applies).

## Knowledge unit schema

Each indexed teaching artifact becomes one or more rows in `knowledge_units`.

Core fields:

| Field | Purpose |
|---|---|
| `persona_id` | Which persona owns this memory |
| `source_id` | Link back to `sources` |
| `content_type` | `principle`, `framework`, `process`, `step_by_step`, `diagnostic_logic`, `example`, `case_study`, `quote`, `story`, `warning`, `visual_framework`, `table`, `diagram`, `transcript_chunk` |
| `chunk_text` | Searchable teaching summary or excerpt |
| `visual_description` | Text derived from diagrams, slides, screenshots, PDF images |
| `topics` | JSON array of topic tags |
| `frameworks` | JSON array of named frameworks |
| `processes` | JSON array of named processes |
| `steps` | JSON array of ordered steps |
| `concepts` | JSON array of concepts |
| `advice_contexts` | JSON array of situations this applies to |
| `examples` | JSON array of examples |
| `quotes` | JSON array of quote objects with `text`, `is_verbatim`, `speaker` |
| `speaker` | Who taught this segment |
| `source_nature` | `written`, `natural_spoken`, `performed_spoken`, `written_performed_as_speech`, `visual`, `mixed`, `uncertain` |
| `evidence_type` | `source_supported`, `inferred_from_sources`, `insufficient_evidence` |
| `confidence` | `strong`, `medium`, `weak`, `insufficient_evidence` |
| `retrieval_priority` | Higher = preferred during ranking |
| `is_new_information` | Whether this unit should be indexed for retrieval |
| `duplicate_of` | Pointer to an earlier equivalent unit, if any |

Source-level metadata lives in `sources`:

| Field | Purpose |
|---|---|
| `source_title` | RSS/yt-dlp title |
| `source_url` | Canonical URL (unique per persona) |
| `source_type` | `youtube`, `podcast`, `web`, `pdf`, `social`, … |
| `source_date` | Published/upload date (ISO UTC) |
| `normalized_title` | Lowercase title for cross-platform dedup |
| `channel_url` | Channel that discovered this source |
| `content_hash` | Hash of processed text (change detection) |
| `status` | `pending`, `processing`, `indexed`, `failed`, `skipped`, … |
| `source_nature` | `written`, `natural_spoken`, … |
| `raw_path`, `error_message` | Paths and failure/skip reasons |

`status=skipped` is used when a podcast episode duplicates an indexed YouTube video (see YouTube-first title dedup).

Embeddings for retrieval live in **Qdrant** (`persona_{persona_id}` collection). SQLite `embeddings` table is a sync registry for backfill/reindex.

## Visual and process extraction

The memory builder extracts knowledge not only from plain text, but also from teaching visuals when they carry instructional value:

- PDF page images
- diagrams and flowcharts
- slides and screenshots
- charts and visual frameworks

Flow:

1. PDF processor extracts embedded images to `sources/processed/{persona}/.../images/`
2. Gemini vision (when `GOOGLE_API_KEY` is set) converts each image into a searchable description
3. `visual_assets_to_units()` creates dedicated knowledge units with:
   - `visual_description`
   - `processes`
   - `steps`
   - `frameworks`
   - `content_type` = `visual_framework`, `diagram`, or `step_by_step`
   - source reference via `source_id`
   - `confidence`

Without an API key, visual assets still produce placeholder descriptions so the pipeline remains deterministic, but detailed diagram parsing requires Gemini.

## New information detection

Daily sync must not blindly store every newly discovered asset.

### Source-level detection

| Case | Behavior |
|---|---|
| New source | Insert as `pending`, process normally |
| Duplicate source | Same URL + same `content_hash` as an indexed source → skip reprocessing |
| Updated source | Same URL, different `content_hash` → reprocess and add new units |
| Unchanged indexed source | Skip |
| YouTube/podcast title match | Podcast source → `skipped` (YouTube already indexed) |

### Knowledge-unit-level detection

| Case | Behavior |
|---|---|
| Exact duplicate | Same fingerprint → `is_new_information=false`, `duplicate_of` set |
| Repeated idea | High text similarity to an existing unit → skip indexing |
| New example | New case/example content → index |
| New framework / process / quote | Distinct structured content → index |
| Clarification | Same framework with new steps or richer process detail → index with higher `retrieval_priority` |

Pipeline summary counters:

- `sources_skipped_unchanged`
- `sources_updated`
- `units_skipped_duplicate`
- `units_repeated_idea`
- `units_clarification`

## Research grounded mode

The advisor runtime only receives retrieval context in `research_grounded` mode.

Rules injected into the prompt:

- use indexed memory for evidence
- do not invent quotes
- verbatim quotes only when memory marks them as verbatim
- if evidence is weak, say so explicitly

Quick mode does not inject RAG context.

## Pipeline telemetry (GUI-ready)

Every sync/build run writes structured progress and cost data to SQLite. This supports a future dashboard that polls realtime status and spend.

### Tables

| Table | Purpose |
|---|---|
| `pipeline_events` | Stage-level progress (`discovery`, `source_fetch`, `source_extract`, `source_index`, `source_done`, `source_error`, …) |
| `api_usage_logs` | Per-call API cost (Gemini, OpenAI embeddings, Scrapfly credits) |
| `sync_runs.cost_usd` | Run total (auto-summed from `api_usage_logs` on finish) |

### CLI polling

```bash
# Human-readable snapshot of latest run
python3 scripts/memory_run_status.py --persona hormozi

# JSON for GUI (incremental events via --after-event-id)
python3 scripts/memory_run_status.py --persona hormozi --run-id 12 --after-event-id 40 --json
```

JSON payload includes:

- `progress.latest_stage` / `latest_message` — current step
- `cost.run_usd` — this run
- `cost.persona_total_usd` — all-time for persona
- `cost.today_usd` — calendar day (local SQLite `datetime('now')`)
- `events[]` — new events since last poll

### Cost estimation

Costs are **estimates** based on token/credit counts and published list prices:

- Gemini: `gemini-2.5-flash` text/audio/image input rates + output rate
- OpenAI: embedding model per-1M-token rate
- Scrapfly: credits × `SCRAPFLY_USD_PER_CREDIT` (default Discovery plan $30/200k)

Set `SCRAPFLY_USD_PER_CREDIT` in `.env` if your plan differs.

### Python API

```python
from memory_builder.telemetry import get_run_progress, list_pipeline_events, get_cost_totals

progress = get_run_progress(store, "hormozi", run_id=12)
events = list_pipeline_events(store, "hormozi", run_id=12, after_id=last_seen_id)
totals = get_cost_totals(store, "hormozi", day="now")
```

## Daily scheduling

Use the included launchd template:

```bash
cp launchd/com.advisoryboard.memory-sync.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.advisoryboard.memory-sync.plist
```

Or run from Hermes cron on the maintainer host:

```bash
python3 /Users/andraspolgar/Developer/advisory-board/scripts/memory_sync.py --persona hormozi
```

## Governance

- Memory updates happen only via maintainer scripts
- Indexed quotes must come from processed sources
- `research_grounded` mode injects retrieval context + quote guard into `ask_advisor.py`
- Doctrine/voice files are not auto-rewritten from memory

## Tests

Unit tests:

```bash
python3 -m unittest discover -s tests -p 'test_memory*.py'
python3 -m unittest discover -s tests -p 'test_retrieval_golden.py'
python3 -m unittest tests.test_telemetry -v
python3 -m unittest tests.test_profile_urls -v
python3 -m unittest tests.test_channel_feeds -v
python3 -m unittest tests.test_social_scrapfly -v
python3 -m unittest tests.test_facebook_scrapfly -v
```

Scrapfly live test (optional, requires `SCRAPFLY_KEY`):

```bash
SCRAPFLY_LIVE_TEST=1 python3 -m unittest tests.test_scrapfly_api_live -v
python3 scripts/test_scrapfly_api.py
```

Golden retrieval queries for Hormozi:

- weak offer diagnosis
- Value Equation steps
- how to increase perceived value
- when to raise prices
- how to diagnose poor conversion

These tests seed a minimal in-memory corpus and verify that retrieval returns chunks containing expected teaching signals. After a real build, run the same queries manually with `memory_search.py` to validate live corpus quality.
