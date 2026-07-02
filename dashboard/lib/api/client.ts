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
  JobCreateRequest,
  JobItem,
  KnowledgeUnitItem,
  UnitStats,
  PersonaConfigResponse,
  PersonaOverview,
  PersonaSummary,
  PipelineEvent,
  RunProgress,
  SearchResponse,
  SoulResponse,
  SourceCandidateItem,
  SourceDetail,
  SourceItem,
  SourceStats,
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

export const fetchPersonas = () => apiGet<PersonaSummary[]>("/personas");
export const fetchPersonaOverview = (personaId: string) =>
  apiGet<PersonaOverview>(`/personas/${encodeURIComponent(personaId)}/overview`);
export const fetchRuns = (personaId: string) =>
  apiGet<SyncRunDetail[]>(`/personas/${encodeURIComponent(personaId)}/runs`);
export const fetchRun = (personaId: string, runId: number) =>
  apiGet<RunProgress>(`/personas/${encodeURIComponent(personaId)}/runs/${runId}`);
export const fetchRunEvents = (personaId: string, runId: number, afterId = 0) =>
  apiGet<PipelineEvent[]>(
    `/personas/${encodeURIComponent(personaId)}/runs/${runId}/events?after_id=${afterId}&limit=200`
  );
export const fetchSources = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<SourceItem[]>(
    `/personas/${encodeURIComponent(personaId)}/sources${query ? `?${query}` : ""}`
  );
};
export const fetchSourceStats = (personaId: string) =>
  apiGet<SourceStats>(`/personas/${encodeURIComponent(personaId)}/sources/stats`);
export const fetchSource = (personaId: string, sourceId: number) =>
  apiGet<SourceDetail>(`/personas/${encodeURIComponent(personaId)}/sources/${sourceId}`);
export const patchSource = (personaId: string, sourceId: number, status: string) =>
  apiSend<SourceItem>(
    `/personas/${encodeURIComponent(personaId)}/sources/${sourceId}`,
    "PATCH",
    { status }
  );
export const fetchUnits = (personaId: string, params: Record<string, string> = {}) => {
  const query = new URLSearchParams(params).toString();
  return apiGet<KnowledgeUnitItem[]>(
    `/personas/${encodeURIComponent(personaId)}/units${query ? `?${query}` : ""}`
  );
};
export const fetchUnitStats = (personaId: string) =>
  apiGet<UnitStats>(`/personas/${encodeURIComponent(personaId)}/units/stats`);
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
) => apiSend(`/personas/${encodeURIComponent(personaId)}/review`, "POST", body);
export const fetchCostSummary = (personaId: string) =>
  apiGet<CostSummary>(`/personas/${encodeURIComponent(personaId)}/costs/summary`);
export const fetchCostBreakdown = (
  personaId: string,
  groupBy: string,
  days = 30
) =>
  apiGet<CostBreakdownItem[]>(
    `/personas/${encodeURIComponent(personaId)}/costs/breakdown?group_by=${groupBy}&days=${days}`
  );
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
