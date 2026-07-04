import type {
  AdvisorConfigFileItem,
  AdvisorConfigFileResponse,
  AdvisorDetail,
  AdvisorPhotoResponse,
  AdvisorSourceConfigResponse,
  AdvisorSummary,
  ChannelItem,
  CostBreakdownItem,
  CostSummary,
  ScrapflyCostSummary,
  ScrapflySubscription,
  JobCreateRequest,
  JobItem,
  KnowledgeUnitDetail,
  KnowledgeUnitItem,
  QuoteItem,
  TranscriptSegmentsResponse,
  TranscriptTextResponse,
  UnitStats,
  PersonaConfigResponse,
  PersonaOverview,
  PersonaSummary,
  PipelineEvent,
  RunProgress,
  SearchResponse,
  SoulResponse,
  ReviewSubmitResponse,
  SourceCandidateItem,
  SourceDetail,
  SourceItem,
  SourceLinkAnalyzeResponse,
  SourceLinkSubmitResponse,
  SourceStats,
  SourceWithMemoryItem,
  SyncRunDetail,
} from "@/lib/api/types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<string> {
  let detail = response.statusText;
  try {
    const body: unknown = await response.json();
    if (
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof (body as { detail: unknown }).detail === "string"
    ) {
      detail = (body as { detail: string }).detail;
    }
  } catch {
    // keep statusText
  }
  return detail;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  return (await response.json()) as T;
}

async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new ApiError(await parseError(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const chunk = bytes.subarray(offset, offset + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

export const ALL_PERSONAS = "__all__";

export const fetchPersonas = () => apiGet<PersonaSummary[]>("/personas");
export const fetchPersonaOverview = (personaId: string) =>
  apiGet<PersonaOverview>(`/personas/${encodeURIComponent(personaId)}/overview`);
export const fetchRuns = (personaId: string) =>
  apiGet<SyncRunDetail[]>(`/personas/${encodeURIComponent(personaId)}/runs`);
export const fetchAllRuns = async () => {
  const personas = await fetchPersonas();
  const runsByPersona = await Promise.all(personas.map((persona) => fetchRuns(persona.persona_id)));
  return runsByPersona
    .flat()
    .sort((left, right) => Date.parse(right.started_at) - Date.parse(left.started_at));
};
export const fetchRun = (personaId: string, runId: number) =>
  apiGet<RunProgress>(`/personas/${encodeURIComponent(personaId)}/runs/${runId}`);
export const fetchRunEvents = (personaId: string, runId: number, afterId = 0, limit = 200) =>
  apiGet<PipelineEvent[]>(
    `/personas/${encodeURIComponent(personaId)}/runs/${runId}/events?after_id=${afterId}&limit=${limit}`
  );
export const stopRun = (personaId: string, runId: number) =>
  apiSend<RunProgress>(
    `/personas/${encodeURIComponent(personaId)}/runs/${runId}/stop`,
    "POST"
  );
export const fetchSources = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<SourceItem[]>(
    `/personas/${encodeURIComponent(personaId)}/sources${query ? `?${query}` : ""}`
  );
};
export const fetchAllSources = async (params: Record<string, string> = {}) => {
  const personas = await fetchPersonas();
  const sourcesByPersona = await Promise.all(
    personas.map((persona) => fetchSources(persona.persona_id, params))
  );
  return sourcesByPersona
    .flat()
    .sort((left, right) => right.id - left.id)
    .slice(0, Number(params.limit) || 500);
};
export const fetchSourceStats = (personaId: string) =>
  apiGet<SourceStats>(`/personas/${encodeURIComponent(personaId)}/sources/stats`);
export const fetchAllSourceStats = async (): Promise<SourceStats> => {
  const personas = await fetchPersonas();
  const statsByPersona = await Promise.all(
    personas.map((persona) => fetchSourceStats(persona.persona_id))
  );
  const statusCounts: Record<string, number> = {};
  const platformMap = new Map<string, Record<string, number>>();
  let total = 0;

  for (const stats of statsByPersona) {
    total += stats.total;
    for (const [status, count] of Object.entries(stats.status_counts)) {
      statusCounts[status] = (statusCounts[status] ?? 0) + count;
    }
    for (const platform of stats.platforms) {
      const existing = platformMap.get(platform.platform) ?? {};
      for (const [status, count] of Object.entries(platform.status_counts)) {
        existing[status] = (existing[status] ?? 0) + count;
      }
      platformMap.set(platform.platform, existing);
    }
  }

  const platforms = [...platformMap.entries()]
    .map(([platform, counts]) => ({
      platform,
      total: Object.values(counts).reduce((sum, count) => sum + count, 0),
      status_counts: counts,
    }))
    .sort((left, right) => right.total - left.total);

  return { total, status_counts: statusCounts, platforms };
};
export const fetchSourcesWithMemory = (
  personaId: string,
  params: Record<string, string> = {}
) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<SourceWithMemoryItem[]>(
    `/personas/${encodeURIComponent(personaId)}/sources/with-memory${query ? `?${query}` : ""}`
  );
};
export const fetchAllSourcesWithMemory = async (params: Record<string, string> = {}) => {
  const personas = await fetchPersonas();
  const sourcesByPersona = await Promise.all(
    personas.map((persona) => fetchSourcesWithMemory(persona.persona_id, params))
  );
  return sourcesByPersona
    .flat()
    .sort((left, right) => right.id - left.id)
    .slice(0, Number(params.limit) || 300);
};
export const fetchSource = (personaId: string, sourceId: number) =>
  apiGet<SourceDetail>(`/personas/${encodeURIComponent(personaId)}/sources/${sourceId}`);
export const patchSource = (personaId: string, sourceId: number, status: string) =>
  apiSend<SourceItem>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}`,
    "PATCH",
    { status }
  );
export const processSource = (personaId: string, sourceId: number) =>
  apiSend<JobItem>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}/process`,
    "POST"
  );
export const deleteSource = (personaId: string, sourceId: number) =>
  apiSend<void>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}`,
    "DELETE"
  );
export const analyzeSourceLink = (body: { url: string; persona_id?: string }) =>
  apiSend<SourceLinkAnalyzeResponse>("/sources/analyze", "POST", body);
export const submitSourceLink = (body: {
  url: string;
  persona_ids: string[];
  process?: boolean;
  persona_id?: string;
}) => apiSend<SourceLinkSubmitResponse>("/sources/submit", "POST", body);
export const fetchUnits = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<KnowledgeUnitItem[]>(
    `/personas/${encodeURIComponent(personaId)}/units${query ? `?${query}` : ""}`
  );
};
export const fetchAllUnits = async (params: Record<string, string> = {}) => {
  const personas = await fetchPersonas();
  const unitsByPersona = await Promise.all(
    personas.map((persona) => fetchUnits(persona.persona_id, params))
  );
  return unitsByPersona
    .flat()
    .sort((left, right) => right.id - left.id)
    .slice(0, Number(params.limit) || 500);
};
export const fetchUnitStats = (personaId: string) =>
  apiGet<UnitStats>(`/personas/${encodeURIComponent(personaId)}/units/stats`);
export const fetchAllUnitStats = async (): Promise<UnitStats> => {
  const personas = await fetchPersonas();
  const statsByPersona = await Promise.all(
    personas.map((persona) => fetchUnitStats(persona.persona_id))
  );
  const merged: UnitStats = {
    total: 0,
    indexed_sources: 0,
    sources_with_units: 0,
    duplicates: 0,
    by_content_type: {},
    by_confidence: {},
    by_platform: {},
  };
  for (const stats of statsByPersona) {
    merged.total += stats.total;
    merged.indexed_sources += stats.indexed_sources;
    merged.sources_with_units += stats.sources_with_units;
    merged.duplicates += stats.duplicates;
    for (const [key, count] of Object.entries(stats.by_content_type)) {
      merged.by_content_type[key] = (merged.by_content_type[key] ?? 0) + count;
    }
    for (const [key, count] of Object.entries(stats.by_confidence)) {
      merged.by_confidence[key] = (merged.by_confidence[key] ?? 0) + count;
    }
    for (const [key, count] of Object.entries(stats.by_platform ?? {})) {
      merged.by_platform[key] = (merged.by_platform[key] ?? 0) + count;
    }
  }
  return merged;
};
export const fetchUnit = (personaId: string, unitId: number) =>
  apiGet<KnowledgeUnitDetail>(`/personas/${encodeURIComponent(personaId)}/units/${unitId}`);
export const fetchQuotes = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<QuoteItem[]>(
    `/personas/${encodeURIComponent(personaId)}/quotes${query ? `?${query}` : ""}`
  );
};
export const fetchSourceTranscript = (personaId: string, sourceId: number, variant: string) =>
  apiGet<TranscriptTextResponse>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}/transcripts/${encodeURIComponent(variant)}`
  );
export const fetchSourceSegments = (personaId: string, sourceId: number) =>
  apiGet<TranscriptSegmentsResponse>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}/segments`
  );
export const searchMemory = (personaId: string, query: string, contextPack: boolean) =>
  apiSend<SearchResponse>(`/personas/${encodeURIComponent(personaId)}/search`, "POST", {
    query,
    top_k: 8,
    context_pack: contextPack,
  });
export const fetchChannels = (personaId: string) =>
  apiGet<ChannelItem[]>(`/personas/${encodeURIComponent(personaId)}/channels`);
export const createChannel = (
  personaId: string,
  body: { channel_type: string; url: string; label?: string; rss_url?: string }
) => apiSend<ChannelItem>(`/personas/${encodeURIComponent(personaId)}/channels`, "POST", body);
export const patchChannel = (
  personaId: string,
  channelId: string,
  body: { archived?: boolean; label?: string }
) =>
  apiSend<ChannelItem>(
    `/personas/${encodeURIComponent(personaId)}/channels/${encodeURIComponent(channelId)}`,
    "PATCH",
    body
  );
export const fetchCandidates = (personaId: string) =>
  apiGet<SourceCandidateItem[]>(`/personas/${encodeURIComponent(personaId)}/candidates`);
export const discoverCandidates = (personaId: string) =>
  apiSend<SourceCandidateItem[]>(
    `/personas/${encodeURIComponent(personaId)}/candidates/discover`,
    "POST"
  );
export const submitReview = (
  personaId: string,
  body: { rejected_indices: number[]; manual_urls: string[] }
) => apiSend<ReviewSubmitResponse>(`/personas/${encodeURIComponent(personaId)}/review`, "POST", body);
export const fetchCostSummary = (personaId: string) =>
  apiGet<CostSummary>(`/personas/${encodeURIComponent(personaId)}/costs/summary`);
export const fetchAllCostSummary = async (): Promise<CostSummary> => {
  const personas = await fetchPersonas();
  const summaries = await Promise.all(
    personas.map((persona) => fetchCostSummary(persona.persona_id))
  );
  return summaries.reduce(
    (merged, summary) => ({
      today_usd: merged.today_usd + summary.today_usd,
      today_calls: merged.today_calls + summary.today_calls,
      total_usd: merged.total_usd + summary.total_usd,
      total_calls: merged.total_calls + summary.total_calls,
      today_api_usd: merged.today_api_usd + summary.today_api_usd,
      today_api_calls: merged.today_api_calls + summary.today_api_calls,
      today_scrapfly_usd: merged.today_scrapfly_usd + summary.today_scrapfly_usd,
      today_scrapfly_calls: merged.today_scrapfly_calls + summary.today_scrapfly_calls,
      today_scrapfly_credits: merged.today_scrapfly_credits + summary.today_scrapfly_credits,
    }),
    {
      today_usd: 0,
      today_calls: 0,
      total_usd: 0,
      total_calls: 0,
      today_api_usd: 0,
      today_api_calls: 0,
      today_scrapfly_usd: 0,
      today_scrapfly_calls: 0,
      today_scrapfly_credits: 0,
    }
  );
};
export const fetchScrapflySubscription = () =>
  apiGet<ScrapflySubscription>("/costs/scrapfly/subscription");
export const fetchScrapflyCostSummary = (personaId: string, days = 30) =>
  apiGet<ScrapflyCostSummary>(
    `/personas/${encodeURIComponent(personaId)}/costs/scrapfly?days=${days}`
  );
export const fetchAllScrapflyCostSummary = async (days = 30): Promise<ScrapflyCostSummary> => {
  const personas = await fetchPersonas();
  const summaries = await Promise.all(
    personas.map((persona) => fetchScrapflyCostSummary(persona.persona_id, days))
  );
  const dailyMap = new Map<string, { day: string; cost_usd: number; api_credits: number; call_count: number }>();
  const operationMap = new Map<string, CostBreakdownItem>();
  let today_usd = 0;
  let today_credits = 0;
  let today_calls = 0;
  let total_usd = 0;
  let total_credits = 0;
  let total_calls = 0;

  for (const summary of summaries) {
    today_usd += summary.today_usd;
    today_credits += summary.today_credits;
    today_calls += summary.today_calls;
    total_usd += summary.total_usd;
    total_credits += summary.total_credits;
    total_calls += summary.total_calls;

    for (const day of summary.daily) {
      const existing = dailyMap.get(day.day) ?? {
        day: day.day,
        cost_usd: 0,
        api_credits: 0,
        call_count: 0,
      };
      dailyMap.set(day.day, {
        day: day.day,
        cost_usd: existing.cost_usd + day.cost_usd,
        api_credits: existing.api_credits + day.api_credits,
        call_count: existing.call_count + day.call_count,
      });
    }

    for (const row of summary.by_operation) {
      const existing = operationMap.get(row.label) ?? {
        label: row.label,
        cost_usd: 0,
        input_tokens: 0,
        output_tokens: 0,
        api_credits: 0,
        call_count: 0,
      };
      operationMap.set(row.label, {
        label: row.label,
        cost_usd: existing.cost_usd + row.cost_usd,
        input_tokens: existing.input_tokens + row.input_tokens,
        output_tokens: existing.output_tokens + row.output_tokens,
        api_credits: existing.api_credits + row.api_credits,
        call_count: existing.call_count + row.call_count,
      });
    }
  }

  return {
    today_usd,
    today_credits,
    today_calls,
    today_cost_per_scrape: today_calls > 0 ? today_usd / today_calls : null,
    total_usd,
    total_credits,
    total_calls,
    total_cost_per_scrape: total_calls > 0 ? total_usd / total_calls : null,
    daily: [...dailyMap.values()].sort((left, right) => left.day.localeCompare(right.day)),
    by_operation: [...operationMap.values()].sort((left, right) => right.cost_usd - left.cost_usd),
  };
};
export const fetchCostBreakdown = (
  personaId: string,
  groupBy: string,
  days = 30,
  excludeProvider?: string
) => {
  const params = new URLSearchParams({
    group_by: groupBy,
    days: String(days),
  });
  if (excludeProvider) {
    params.set("exclude_provider", excludeProvider);
  }
  return apiGet<CostBreakdownItem[]>(
    `/personas/${encodeURIComponent(personaId)}/costs/breakdown?${params.toString()}`
  );
};
function mergeCostBreakdownRows(rows: CostBreakdownItem[]): CostBreakdownItem[] {
  const merged = new Map<string, CostBreakdownItem>();
  for (const row of rows) {
    const existing = merged.get(row.label) ?? {
      label: row.label,
      cost_usd: 0,
      input_tokens: 0,
      output_tokens: 0,
      api_credits: 0,
      call_count: 0,
    };
    merged.set(row.label, {
      label: row.label,
      cost_usd: existing.cost_usd + row.cost_usd,
      input_tokens: existing.input_tokens + row.input_tokens,
      output_tokens: existing.output_tokens + row.output_tokens,
      api_credits: existing.api_credits + row.api_credits,
      call_count: existing.call_count + row.call_count,
    });
  }
  return [...merged.values()].sort((left, right) => right.cost_usd - left.cost_usd);
}
export const fetchAllCostBreakdown = async (
  groupBy: string,
  days = 30,
  excludeProvider?: string
) => {
  const personas = await fetchPersonas();
  const breakdowns = await Promise.all(
    personas.map((persona) => fetchCostBreakdown(persona.persona_id, groupBy, days, excludeProvider))
  );
  return mergeCostBreakdownRows(breakdowns.flat());
};
export const fetchLogs = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<PipelineEvent[]>(
    `/personas/${encodeURIComponent(personaId)}/logs${query ? `?${query}` : ""}`
  );
};
export const fetchJobs = () => apiGet<JobItem[]>("/jobs");
export const createJob = (body: JobCreateRequest) => apiSend<JobItem>("/jobs", "POST", body);
export const stopJob = (jobId: string) => apiSend<JobItem>(`/jobs/${jobId}`, "DELETE");
export const fetchAdvisors = () => apiGet<AdvisorSummary[]>("/advisors");
export const fetchAdvisor = (advisorId: string) =>
  apiGet<AdvisorDetail>(`/advisors/${encodeURIComponent(advisorId)}`);
export const fetchSoul = (advisorId: string) =>
  apiGet<SoulResponse>(`/advisors/${encodeURIComponent(advisorId)}/soul`);
export const deploySoul = (advisorId: string, content?: string) =>
  apiSend(`/advisors/${encodeURIComponent(advisorId)}/deploy`, "POST", { content });
export const uploadAdvisorPhoto = async (advisorId: string, file: File) =>
  apiSend<AdvisorPhotoResponse>(`/advisors/${encodeURIComponent(advisorId)}/photo`, "POST", {
    filename: file.name,
    content_type: file.type,
    data_base64: await fileToBase64(file),
  });
export const fetchAdvisorConfigFiles = (advisorId: string) =>
  apiGet<AdvisorConfigFileItem[]>(
    `/advisors/${encodeURIComponent(advisorId)}/config-files`
  );
export const fetchAdvisorConfigFile = (advisorId: string, fileKey: string) =>
  apiGet<AdvisorConfigFileResponse>(
    `/advisors/${encodeURIComponent(advisorId)}/config-files/${encodeURIComponent(fileKey)}`
  );
export const saveAdvisorConfigFile = (advisorId: string, fileKey: string, content: string) =>
  apiSend<AdvisorConfigFileResponse>(
    `/advisors/${encodeURIComponent(advisorId)}/config-files/${encodeURIComponent(fileKey)}`,
    "PUT",
    { content }
  );
export const createAdvisorConfigFile = (advisorId: string, fileKey: string) =>
  apiSend<AdvisorConfigFileResponse>(
    `/advisors/${encodeURIComponent(advisorId)}/config-files/${encodeURIComponent(fileKey)}`,
    "POST"
  );
export const fetchAdvisorSourceConfig = (advisorId: string) =>
  apiGet<AdvisorSourceConfigResponse>(
    `/advisors/${encodeURIComponent(advisorId)}/source-config`
  );
export const saveAdvisorSourceConfig = (advisorId: string, config: Record<string, unknown>) =>
  apiSend(`/advisors/${encodeURIComponent(advisorId)}/source-config`, "PUT", { config });
export const createAdvisorSourceConfig = (advisorId: string) =>
  apiSend(`/advisors/${encodeURIComponent(advisorId)}/source-config`, "POST");
export const fetchPersonaConfig = (personaId: string) =>
  apiGet<PersonaConfigResponse>(`/personas/${encodeURIComponent(personaId)}/config`);
export const savePersonaConfig = (personaId: string, config: Record<string, unknown>) =>
  apiSend(`/personas/${encodeURIComponent(personaId)}/config`, "PUT", { config });
export const createPersona = (body: { persona_id: string; display_name: string }) =>
  apiSend<PersonaSummary>("/personas", "POST", body);
