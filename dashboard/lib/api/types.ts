export interface PersonaSummary {
  persona_id: string;
  display_name: string;
}

export interface CostSummary {
  today_usd: number;
  today_calls: number;
  total_usd: number;
  total_calls: number;
  today_api_usd: number;
  today_api_calls: number;
  today_scrapfly_usd: number;
  today_scrapfly_calls: number;
  today_scrapfly_credits: number;
}

export interface RunSummary {
  run_id: number;
  started_at: string;
  finished_at: string | null;
  sources_discovered: number;
  sources_processed: number;
  units_created: number;
  errors: number;
  cost_usd: number;
}

export interface ActiveRun {
  run_id: number;
  started_at: string;
  latest_stage: string;
  latest_message: string;
  current_platform: string;
  current_title: string;
  current_url: string;
  current_stage: string;
  done_count: number;
  error_count: number;
  skip_count: number;
  pending_by_platform: Record<string, number>;
  cost_run_usd: number;
}

export interface PersonaOverview {
  persona_id: string;
  display_name: string;
  source_status_counts: Record<string, number>;
  source_total: number;
  unit_count: number;
  cost: CostSummary;
  last_run: RunSummary | null;
  active_run: ActiveRun | null;
}

export interface SyncRunDetail {
  run_id: number;
  persona_id: string;
  started_at: string;
  finished_at: string | null;
  stopped_at: string | null;
  stop_reason: string | null;
  last_activity_at: string | null;
  active_duration_seconds: number;
  sources_discovered: number;
  sources_processed: number;
  units_created: number;
  units_skipped_duplicate: number;
  errors: number;
  cost_usd: number;
  summary: string | null;
  status: string;
  done_count: number;
  error_count: number;
  skip_count: number;
  api_calls: number;
  run_mode: string;
}

export interface RunProgress {
  run_id: number;
  persona_id: string;
  started_at: string;
  finished_at: string | null;
  stopped_at: string | null;
  stop_reason: string | null;
  last_activity_at: string | null;
  active_duration_seconds: number;
  status: string;
  latest_stage: string;
  latest_message: string;
  events_count: number;
  sources_processed: number;
  sources_discovered: number;
  run_mode: string;
  cost_run_usd: number;
  cost_persona_usd: number;
  cost_today_usd: number;
  current_platform: string;
  current_title: string;
  current_url: string;
  current_stage: string;
  done_count: number;
  error_count: number;
  skip_count: number;
}

export interface PipelineEvent {
  id: number;
  persona_id: string;
  run_id: number | null;
  source_id: number | null;
  stage: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SourceItem {
  id: number;
  persona_id: string;
  source_title: string | null;
  source_url: string;
  source_type: string;
  source_date: string | null;
  status: string;
  channel_url: string | null;
  error_message: string | null;
  processed_at: string | null;
  platform: string;
  media_format: string;
}

export interface SourceDetail extends SourceItem {
  content_hash: string | null;
  raw_path: string | null;
  unit_count: number;
  processed_text: string | null;
  transcript_status: string;
  transcript_variants: TranscriptVariantItem[];
}

export interface TranscriptVariantItem {
  key: string;
  label: string;
  available: boolean;
  char_count: number;
}

export interface TranscriptTextResponse {
  source_id: number;
  variant: string;
  label: string;
  text: string;
  char_count: number;
}

export interface TranscriptSegmentItem {
  segment_id: string;
  speaker: string;
  speaker_type: string;
  text: string;
  start_seconds: number | null;
  end_seconds: number | null;
  confidence: string;
}

export interface TranscriptSegmentsResponse {
  source_id: number;
  display_name: string;
  transcription_mode: string;
  segments: TranscriptSegmentItem[];
}

export interface QuoteItem {
  unit_id: number;
  source_id: number;
  text: string;
  speaker: string | null;
  source_title: string | null;
  source_url: string | null;
  source_link: string | null;
  segment_id: string | null;
  start_seconds: number | null;
  end_seconds: number | null;
  is_verbatim: boolean;
  content_type: string;
  confidence: string;
}

export interface SourceWithMemoryItem extends SourceItem {
  unit_count: number;
  strong_count: number;
  medium_count: number;
  weak_count: number;
  duplicate_count: number;
  content_type_counts: Record<string, number>;
  latest_unit_preview: string | null;
  latest_event_stage: string | null;
  latest_event_message: string | null;
  latest_event_at: string | null;
  needs_attention: boolean;
}

export interface SourcePlatformStat {
  platform: string;
  total: number;
  status_counts: Record<string, number>;
}

export interface SourceStats {
  total: number;
  status_counts: Record<string, number>;
  platforms: SourcePlatformStat[];
}

export interface SourceLinkPersonaMatch {
  persona_id: string;
  display_name: string;
  confidence: number;
  signals: string[];
  selected: boolean;
}

export interface SourceLinkAnalyzeResponse {
  url: string;
  normalized_url: string;
  kind: string;
  source_type: string;
  platform: string;
  title: string;
  channel_url: string | null;
  processable: boolean;
  message: string;
  matched_personas: SourceLinkPersonaMatch[];
}

export interface SourceLinkSubmitPersonaResult {
  persona_id: string;
  source_id: number | null;
  channel_id: string | null;
  status: string;
  job_id: string | null;
  message: string;
}

export interface SourceLinkSubmitResponse {
  url: string;
  normalized_url: string;
  kind: string;
  source_type: string;
  platform: string;
  title: string;
  results: SourceLinkSubmitPersonaResult[];
}

export interface KnowledgeUnitItem {
  id: number;
  persona_id: string;
  source_id: number;
  content_type: string;
  chunk_text: string;
  confidence: string;
  is_new_information: boolean;
  duplicate_of: number | null;
  source_title: string | null;
  source_url: string | null;
  source_type: string;
  channel_url: string | null;
  frameworks: string[];
  processes: string[];
  steps: string[];
  quotes: Array<Record<string, unknown>>;
  evidence_type: string;
  retrieval_priority: number;
}

export interface KnowledgeUnitDetail extends KnowledgeUnitItem {
  visual_description: string;
  topics: string[];
  concepts: string[];
  advice_contexts: string[];
  examples: string[];
  speaker: string | null;
  source_nature: string;
}

export interface UnitStats {
  total: number;
  indexed_sources: number;
  sources_with_units: number;
  duplicates: number;
  by_content_type: Record<string, number>;
  by_confidence: Record<string, number>;
  by_platform: Record<string, number>;
}

export interface SearchHit {
  unit_id: number;
  score: number;
  chunk_text: string;
  content_type: string;
  confidence: string;
  source_title: string;
  source_url: string;
  source_date: string | null;
  source_type: string;
  channel_url: string | null;
  evidence_type: string;
  frameworks: string[];
  processes: string[];
  steps: string[];
  quotes: Array<Record<string, unknown>>;
  retrieval_priority: number;
  is_new_information: boolean;
}

export interface SearchResponse {
  hits: SearchHit[];
  context_pack: string | null;
}

export interface ChannelItem {
  channel_id: string;
  type: string;
  url: string;
  label: string;
  priority: number;
  rss_url: string | null;
  latest_published_at: string | null;
  last_discovered_at: string | null;
  added_at: string;
  archived: boolean;
}

export interface SourceCandidateItem {
  index: number;
  url: string;
  platform: string;
  confidence: number;
  discovery_source: string;
  username: string;
  signals: string[];
  status: string;
}

export interface ReviewSubmitResponse {
  approved_count: number;
  reviewed_at: string;
  reviewed_by: string;
}

export interface CostBreakdownItem {
  label: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  api_credits: number;
  call_count: number;
}

export interface ScrapflySubscription {
  plan_name: string;
  period_start: string;
  period_end: string;
  credits_used: number;
  credits_limit: number;
  credits_remaining: number;
  plan_price_usd: number;
  usage_usd: number;
  usd_per_credit: number;
  quota_reached: boolean;
  concurrent_usage: number;
  concurrent_limit: number;
  project_name: string;
}

export interface ScrapflyDailyUsage {
  day: string;
  cost_usd: number;
  api_credits: number;
  call_count: number;
}

export interface ScrapflyCostSummary {
  today_usd: number;
  today_credits: number;
  today_calls: number;
  today_cost_per_scrape: number | null;
  total_usd: number;
  total_credits: number;
  total_calls: number;
  total_cost_per_scrape: number | null;
  daily: ScrapflyDailyUsage[];
  by_operation: CostBreakdownItem[];
}

export interface JobItem {
  job_id: string;
  persona_id: string;
  command: string[];
  status: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  log_tail: string[];
}

export interface JobCreateRequest {
  persona_id: string;
  kind: "build" | "sync";
  only_platform?: string | null;
  limit?: number | null;
  retry_failed?: boolean;
  skip_discovery?: boolean;
  dry_run?: boolean;
  discover_only?: boolean;
  discovery_limit?: number | null;
}

export interface AdvisorSummary {
  advisor_id: string;
  name: string;
  role: string;
  photo_url: string | null;
}

export interface AdvisorDetail {
  advisor_id: string;
  config: {
    name: string;
    role: string;
    core_traits: string[];
  };
  global: Record<string, unknown>;
  markdown: string;
  photo_url: string | null;
}

export interface AdvisorPhotoResponse {
  advisor_id: string;
  photo_url: string | null;
}

export interface SoulResponse {
  advisor_id: string;
  rendered: string;
  deployed: string | null;
  deployed_exists: boolean;
}

export type AdvisorConfigKind = "json" | "yaml" | "markdown";

export interface AdvisorConfigFileItem {
  key: string;
  label: string;
  path: string;
  kind: AdvisorConfigKind;
  exists: boolean;
  shared: boolean;
  can_create: boolean;
}

export interface AdvisorConfigFileResponse extends AdvisorConfigFileItem {
  content: string | null;
}

export interface AdvisorSourceConfigResponse {
  advisor_id: string;
  config: Record<string, unknown>;
  raw_yaml: string;
}

export interface PersonaConfigResponse {
  config: Record<string, unknown>;
  raw_yaml: string;
}
