from __future__ import annotations

from pydantic import BaseModel, Field


class PersonaSummary(BaseModel):
    persona_id: str
    display_name: str


class CostSummary(BaseModel):
    today_usd: float
    today_calls: int
    total_usd: float
    total_calls: int


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


class RunProgressResponse(BaseModel):
    run_id: int
    persona_id: str
    started_at: str
    finished_at: str | None
    status: str
    latest_stage: str
    latest_message: str
    events_count: int
    sources_processed: int
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
    source_title: str | None
    source_url: str
    source_type: str
    source_date: str | None
    status: str
    channel_url: str | None
    error_message: str | None
    processed_at: str | None
    platform: str = ""


class SourceDetail(SourceItem):
    content_hash: str | None
    raw_path: str | None
    unit_count: int = 0
    processed_text: str | None = None


class SourcePatchRequest(BaseModel):
    status: str | None = None


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


class JobCreateRequest(BaseModel):
    persona_id: str
    kind: str = "build"
    only_platform: str | None = None
    limit: int | None = None
    retry_failed: bool = False
    skip_discovery: bool = False
    dry_run: bool = False


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
