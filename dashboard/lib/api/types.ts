export interface PersonaSummary {
  persona_id: string;
  display_name: string;
}

export interface CostSummary {
  today_usd: number;
  today_calls: number;
  total_usd: number;
  total_calls: number;
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
}

export interface RunProgress {
  run_id: number;
  persona_id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  latest_stage: string;
  latest_message: string;
  events_count: number;
  sources_processed: number;
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
  source_title: string | null;
  source_url: string;
  source_type: string;
  source_date: string | null;
  status: string;
  channel_url: string | null;
  error_message: string | null;
  processed_at: string | null;
  platform: string;
}

export interface SourceDetail extends SourceItem {
  content_hash: string | null;
  raw_path: string | null;
  unit_count: number;
  processed_text: string | null;
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

export interface KnowledgeUnitItem {
  id: number;
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

export interface CostBreakdownItem {
  label: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  api_credits: number;
  call_count: number;
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
