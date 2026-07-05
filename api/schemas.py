from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PersonaSummary(BaseModel):
    persona_id: str
    display_name: str


class CostSummary(BaseModel):
    today_usd: float
    today_calls: int
    total_usd: float
    total_calls: int
    today_api_usd: float = 0
    today_api_calls: int = 0
    today_scrapfly_usd: float = 0
    today_scrapfly_calls: int = 0
    today_scrapfly_credits: float = 0


class RunSummary(BaseModel):
    run_id: int
    started_at: str
    finished_at: str | None
    sources_discovered: int
    sources_processed: int
    units_created: int
    errors: int
    cost_usd: float


class ActiveRun(BaseModel):
    run_id: int
    started_at: str
    latest_stage: str
    latest_message: str
    current_platform: str
    current_title: str
    current_url: str
    current_stage: str
    done_count: int
    error_count: int
    skip_count: int
    pending_by_platform: dict[str, int]
    cost_run_usd: float


class PersonaOverview(BaseModel):
    persona_id: str
    display_name: str
    source_status_counts: dict[str, int]
    source_total: int
    unit_count: int
    cost: CostSummary
    last_run: RunSummary | None
    active_run: ActiveRun | None


class SyncRunDetail(BaseModel):
    run_id: int
    persona_id: str
    started_at: str
    finished_at: str | None
    stopped_at: str | None = None
    stop_reason: str | None = None
    last_activity_at: str | None = None
    active_duration_seconds: int = 0
    sources_discovered: int
    sources_processed: int
    units_created: int
    units_skipped_duplicate: int
    errors: int
    cost_usd: float
    summary: str | None
    status: str
    done_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    api_calls: int = 0
    run_mode: str = "—"


class RunProgressResponse(BaseModel):
    run_id: int
    persona_id: str
    started_at: str
    finished_at: str | None
    stopped_at: str | None = None
    stop_reason: str | None = None
    last_activity_at: str | None = None
    active_duration_seconds: int = 0
    status: str
    latest_stage: str
    latest_message: str
    events_count: int
    sources_processed: int
    sources_discovered: int = 0
    run_mode: str = "—"
    cost_run_usd: float
    cost_persona_usd: float
    cost_today_usd: float
    current_platform: str
    current_title: str
    current_url: str
    current_stage: str
    done_count: int
    error_count: int
    skip_count: int


class PipelineEvent(BaseModel):
    id: int
    persona_id: str
    run_id: int | None
    source_id: int | None
    stage: str
    message: str
    metadata: dict
    created_at: str


class SourceItem(BaseModel):
    id: int
    persona_id: str
    source_title: str | None
    source_url: str
    source_type: str
    source_date: str | None
    status: str
    channel_url: str | None
    error_message: str | None
    processed_at: str | None
    platform: str = ""
    media_format: str = "unknown"


class SourceDetail(SourceItem):
    content_hash: str | None
    raw_path: str | None
    unit_count: int = 0
    processed_text: str | None = None
    transcript_status: str = "unlabeled"
    transcript_variants: list["TranscriptVariantItem"] = Field(default_factory=list)


class TranscriptVariantItem(BaseModel):
    key: str
    label: str
    available: bool
    char_count: int = 0


class TranscriptTextResponse(BaseModel):
    source_id: int
    variant: str
    label: str
    text: str
    char_count: int


class TranscriptSegmentItem(BaseModel):
    segment_id: str
    speaker: str
    speaker_type: str
    text: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    confidence: str = "medium"


class TranscriptSegmentsResponse(BaseModel):
    source_id: int
    display_name: str = ""
    transcription_mode: str = "diarized"
    segments: list[TranscriptSegmentItem]


class QuoteItem(BaseModel):
    unit_id: int
    source_id: int
    text: str
    speaker: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_link: str | None = None
    segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    is_verbatim: bool = True
    content_type: str = "quote"
    confidence: str = "medium"


class SourceWithMemoryItem(SourceItem):
    unit_count: int = 0
    strong_count: int = 0
    medium_count: int = 0
    weak_count: int = 0
    duplicate_count: int = 0
    content_type_counts: dict[str, int] = Field(default_factory=dict)
    latest_unit_preview: str | None = None
    latest_event_stage: str | None = None
    latest_event_message: str | None = None
    latest_event_at: str | None = None
    needs_attention: bool = False


class SourcePatchRequest(BaseModel):
    status: str | None = None


class SourceLinkAnalyzeRequest(BaseModel):
    url: str
    persona_id: str | None = None


class SourceLinkPersonaMatch(BaseModel):
    persona_id: str
    display_name: str
    confidence: float
    signals: list[str] = Field(default_factory=list)
    selected: bool = False


class SourceLinkAnalyzeResponse(BaseModel):
    url: str
    normalized_url: str
    kind: str
    source_type: str
    platform: str
    title: str
    channel_url: str | None = None
    processable: bool
    message: str = ""
    matched_personas: list[SourceLinkPersonaMatch] = Field(default_factory=list)


class SourceLinkSubmitRequest(BaseModel):
    url: str
    persona_ids: list[str] = Field(default_factory=list)
    process: bool = True
    persona_id: str | None = None


class SourceLinkSubmitPersonaResult(BaseModel):
    persona_id: str
    source_id: int | None = None
    channel_id: str | None = None
    status: str
    job_id: str | None = None
    message: str = ""


class SourceLinkSubmitResponse(BaseModel):
    url: str
    normalized_url: str
    kind: str
    source_type: str
    platform: str
    title: str
    results: list[SourceLinkSubmitPersonaResult] = Field(default_factory=list)


class SourcePlatformStat(BaseModel):
    platform: str
    total: int
    status_counts: dict[str, int]


class SourceStatsResponse(BaseModel):
    total: int
    status_counts: dict[str, int]
    platforms: list[SourcePlatformStat]


class KnowledgeUnitItem(BaseModel):
    id: int
    persona_id: str
    source_id: int
    content_type: str
    chunk_text: str
    confidence: str
    is_new_information: bool
    duplicate_of: int | None
    source_title: str | None = None
    source_url: str | None = None
    source_type: str = ""
    channel_url: str | None = None
    frameworks: list[str] = Field(default_factory=list)
    processes: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    evidence_type: str = "source_supported"
    retrieval_priority: int = 50


class KnowledgeUnitDetail(KnowledgeUnitItem):
    visual_description: str = ""
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    advice_contexts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    speaker: str | None = None
    source_nature: str = ""


class UnitStats(BaseModel):
    total: int
    indexed_sources: int
    sources_with_units: int
    duplicates: int
    by_content_type: dict[str, int]
    by_confidence: dict[str, int]
    by_platform: dict[str, int] = Field(default_factory=dict)


class SearchHit(BaseModel):
    unit_id: int
    score: float
    chunk_text: str
    content_type: str
    confidence: str
    source_title: str
    source_url: str
    source_date: str | None
    source_type: str = ""
    channel_url: str | None = None
    evidence_type: str
    frameworks: list[str]
    processes: list[str]
    steps: list[str]
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_priority: int = 50
    is_new_information: bool = True


class SearchRequest(BaseModel):
    query: str
    top_k: int = 8
    context_pack: bool = False


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    context_pack: str | None = None


class ChannelItem(BaseModel):
    channel_id: str
    type: str
    url: str
    label: str
    priority: int
    rss_url: str | None
    latest_published_at: str | None
    last_discovered_at: str | None
    added_at: str
    archived: bool


class ChannelCreateRequest(BaseModel):
    channel_type: str
    url: str
    label: str = ""
    rss_url: str | None = None


class ChannelPatchRequest(BaseModel):
    archived: bool | None = None
    label: str | None = None


class SourceCandidateItem(BaseModel):
    index: int
    url: str
    platform: str
    confidence: float
    discovery_source: str
    username: str
    signals: list[str]
    status: str


class ReviewSubmitRequest(BaseModel):
    rejected_indices: list[int] = Field(default_factory=list)
    manual_urls: list[str] = Field(default_factory=list)
    reviewed_by: str = "dashboard"


class CostBreakdownItem(BaseModel):
    label: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    api_credits: float
    call_count: int


class ScrapflySubscription(BaseModel):
    plan_name: str
    period_start: str
    period_end: str
    credits_used: int
    credits_limit: int
    credits_remaining: int
    plan_price_usd: float
    usage_usd: float
    usd_per_credit: float
    quota_reached: bool
    concurrent_usage: int
    concurrent_limit: int
    project_name: str


class ScrapflyDailyUsage(BaseModel):
    day: str
    cost_usd: float
    api_credits: float
    call_count: int


class ScrapflyCostSummary(BaseModel):
    today_usd: float
    today_credits: float
    today_calls: int
    today_cost_per_scrape: float | None = None
    total_usd: float
    total_credits: float
    total_calls: int
    total_cost_per_scrape: float | None = None
    daily: list[ScrapflyDailyUsage] = Field(default_factory=list)
    by_operation: list[CostBreakdownItem] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    persona_id: str
    kind: str = "build"
    only_platform: str | None = None
    limit: int | None = None
    retry_failed: bool = False
    skip_discovery: bool = False
    dry_run: bool = False
    discover_only: bool = False
    discovery_limit: int | None = None


class JobItem(BaseModel):
    job_id: str
    persona_id: str
    command: list[str]
    status: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    exit_code: int | None
    log_tail: list[str]


class AdvisorSummary(BaseModel):
    advisor_id: str
    name: str
    role: str
    photo_url: str | None = None


class AdvisorPhotoUploadRequest(BaseModel):
    filename: str
    content_type: str
    data_base64: str


class AdvisorPhotoResponse(BaseModel):
    advisor_id: str
    photo_url: str | None


class SoulResponse(BaseModel):
    advisor_id: str
    rendered: str
    deployed: str | None
    deployed_exists: bool


class SoulDeployRequest(BaseModel):
    content: str | None = None


class AdvisorConfigFileItem(BaseModel):
    key: str
    label: str
    path: str
    kind: str
    exists: bool
    shared: bool = False
    can_create: bool = False


class AdvisorConfigFileResponse(AdvisorConfigFileItem):
    content: str | None = None


class AdvisorConfigFileUpdateRequest(BaseModel):
    content: str
