"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Layers, Link2, Search, Cancel as XIcon } from "@/lib/icons";

import { SourceDetailModal } from "@/components/sources/source-detail-modal";
import { AddSourceLinkModal } from "@/components/sources/add-source-link-modal";
import { QueryError } from "@/components/shared/api-guard";
import { PageHeader } from "@/components/shared/page-header";
import { SourceIdentity } from "@/components/shared/source-identity";
import { SourceStatusChip } from "@/components/shared/source-status-chip";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ChannelTypeIcon } from "@/components/channels/channel-type-icon";
import { DiscoveryLimitButton } from "@/components/sources/discovery-limit-button";
import { ProcessLimitButton } from "@/components/sources/process-limit-button";
import { SourcePipelineProgress } from "@/components/sources/source-pipeline-progress";
import { SourceRowActions } from "@/components/sources/source-row-actions";
import { useSourceDiscovery } from "@/components/sources/use-source-discovery";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchAllSourceStats, fetchAllSources, ALL_PERSONAS, fetchSources, fetchSourceStats } from "@/lib/api/client";
import type { SourceItem, SourcePlatformStat } from "@/lib/api/types";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";
import { formatSourceDateStack } from "@/lib/format";
import {
  sortSourceStatusEntries,
  sourceStatusMeta,
  SOURCE_ACTIVE_STATUSES,
  SOURCE_STATUS_ORDER,
} from "@/lib/source-status";
import { cn } from "@/lib/utils";

/** Platform label (API) → icon type a ChannelTypeIcon-hoz. */
const PLATFORM_ICON_TYPES: Record<string, string> = {
  YouTube: "youtube",
  Spotify: "spotify",
  "Apple Podcasts": "apple_podcast",
  Podcast: "podcast_rss",
  X: "x",
  Instagram: "instagram",
  Facebook: "facebook",
  LinkedIn: "linkedin",
  TikTok: "tiktok",
  Web: "web",
};

const PLATFORM_FILTER_TO_API: Record<string, string> = {
  YouTube: "youtube",
  Spotify: "spotify",
  "Apple Podcasts": "apple_podcast",
  Podcast: "podcast_rss",
  X: "x",
  Instagram: "instagram",
  Facebook: "facebook",
  LinkedIn: "linkedin",
  TikTok: "tiktok",
  Web: "web",
};

const MEDIA_FORMAT_ORDER = ["text", "image", "video", "audio"] as const;
const MEDIA_FORMAT_LABELS: Record<string, string> = {
  text: "Szöveg",
  image: "Kép",
  video: "Videó",
  audio: "Hang",
  unknown: "Ismeretlen",
};

function StatusChip({
  status,
  count,
  active,
  onClick,
}: {
  status: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  const meta = sourceStatusMeta(status);
  return (
    <Button
      type="button"
      variant="outline"
      size="xs"
      onClick={onClick}
      className={cn(
        "h-auto rounded-full px-2.5 py-1 text-xs font-medium",
        meta.chipClass,
        active
          ? "ring-2 ring-primary/40 ring-offset-1 ring-offset-background"
          : "opacity-80 hover:opacity-100"
      )}
    >
      <span className={cn("size-1.5 rounded-full", meta.dotClass)} aria-hidden />
      {meta.label}
      <span className="tabular-nums">{count}</span>
    </Button>
  );
}

function PlatformCard({
  stat,
  active,
  onClick,
}: {
  stat: SourcePlatformStat;
  active: boolean;
  onClick: () => void;
}) {
  const indexed = stat.status_counts["indexed"] ?? 0;
  const failed = stat.status_counts["failed"] ?? 0;
  const ratio = stat.total > 0 ? indexed / stat.total : 0;
  const iconType = PLATFORM_ICON_TYPES[stat.platform] ?? "web";

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      className={cn(
        "group h-auto flex-col items-stretch gap-2 rounded-xl bg-card p-3 text-left ring-1 transition-all hover:bg-card",
        active
          ? "ring-2 ring-primary shadow-sm"
          : "ring-foreground/10 hover:ring-foreground/25 hover:shadow-sm"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <ChannelTypeIcon type={iconType} size="sm" />
        <span className="font-heading text-xl font-semibold tabular-nums">{stat.total}</span>
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{stat.platform}</p>
        <p className="text-xs text-muted-foreground">
          {indexed} indexelve
          {failed > 0 ? <span className="text-red-500"> · {failed} hibás</span> : null}
        </p>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${Math.round(ratio * 100)}%` }}
        />
      </div>
    </Button>
  );
}

function AllPlatformsCard({
  total,
  indexed,
  active,
  onClick,
}: {
  total: number;
  indexed: number;
  active: boolean;
  onClick: () => void;
}) {
  const ratio = total > 0 ? indexed / total : 0;
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      className={cn(
        "group h-auto flex-col items-stretch gap-2 rounded-xl bg-card p-3 text-left ring-1 transition-all hover:bg-card",
        active
          ? "ring-2 ring-primary shadow-sm"
          : "ring-foreground/10 hover:ring-foreground/25 hover:shadow-sm"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-lg border bg-muted text-muted-foreground">
          <Layers className="size-4" />
        </span>
        <span className="font-heading text-xl font-semibold tabular-nums">{total}</span>
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">Összes forrás</p>
        <p className="text-xs text-muted-foreground">{indexed} indexelve</p>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all"
          style={{ width: `${Math.round(ratio * 100)}%` }}
        />
      </div>
    </Button>
  );
}

export function SourcesPageStandalone() {
  const { personaId, setPersonaId } = usePersonaPageState();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Források"
        description="Link hozzáadás, forrás keresés és feldolgozás — státusz és részletek."
        personaId={personaId}
        onPersonaChange={setPersonaId}
        personaAllowAll
      />
      <SourcesPageClient personaId={personaId} />
    </div>
  );
}

export function SourcesPageClient({ personaId }: { personaId: string }) {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { personas } = usePersonaOptions();
  const showAllPersonas = personaId === ALL_PERSONAS;
  const personaLabels = useMemo(
    () => Object.fromEntries(personas.map((persona) => [persona.persona_id, persona.display_name])),
    [personas]
  );
  const [status, setStatus] = useState("");
  const [platform, setPlatform] = useState("");
  const [media, setMedia] = useState("");
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [addLinkOpen, setAddLinkOpen] = useState(false);

  const discoveryPlatform = PLATFORM_FILTER_TO_API[platform] ?? "";
  const discoveryPersonaId = showAllPersonas ? "" : personaId;
  const discovery = useSourceDiscovery(discoveryPersonaId, discoveryPlatform);
  const discoveryActive = discovery.isRunning && discovery.isDiscoverOnlyJob;
  const processActive = discovery.isRunning && discovery.isProcessJob;
  const pipelineActive = discoveryActive || processActive;
  const anyJobRunning = discovery.isRunning;

  const sourcesPollInterval = (sources: SourceItem[]) => {
    const hasActiveSources = sources.some((item) => SOURCE_ACTIVE_STATUSES.includes(item.status));
    return pipelineActive || hasActiveSources ? 2000 : false;
  };

  const sourcesQueryKey = ["sources", personaId, status, platform, media, search] as const;
  const getSourcesPollInterval = () =>
    sourcesPollInterval(queryClient.getQueryData<SourceItem[]>(sourcesQueryKey) ?? []);

  const statsQuery = useQuery({
    queryKey: ["source-stats", personaId],
    queryFn: () => (showAllPersonas ? fetchAllSourceStats() : fetchSourceStats(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: getSourcesPollInterval,
  });

  const sourceParams = Object.fromEntries(
    Object.entries({ status, platform, media, search, limit: "500" }).filter(([, value]) =>
      Boolean(value)
    )
  );

  const sourcesQuery = useQuery({
    queryKey: sourcesQueryKey,
    queryFn: () =>
      showAllPersonas ? fetchAllSources(sourceParams) : fetchSources(personaId, sourceParams),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: (query) => sourcesPollInterval(query.state.data ?? []),
  });

  const stats = statsQuery.data;
  const sources = sourcesQuery.data ?? [];

  // A státusz chipek a kiválasztott platform bontását mutatják, ha van szűrés.
  const statusCounts = useMemo(() => {
    if (!stats) return {};
    if (!platform) return stats.status_counts;
    return stats.platforms.find((p) => p.platform === platform)?.status_counts ?? {};
  }, [stats, platform]);

  const hasFilter = Boolean(status || platform || media || search);

  useEffect(() => {
    if (selectedIndex === null || showAllPersonas) return;
    const current = sources[selectedIndex];
    if (!current || current.persona_id !== personaId) setSelectedIndex(null);
  }, [personaId, showAllPersonas, selectedIndex, sources]);

  useEffect(() => {
    const sourceParam = searchParams.get("source");
    if (!sourceParam || showAllPersonas || sources.length === 0) return;
    const parsed = Number.parseInt(sourceParam, 10);
    if (Number.isNaN(parsed)) return;
    const index = sources.findIndex(
      (source) => source.id === parsed && source.persona_id === personaId
    );
    if (index >= 0) setSelectedIndex(index);
  }, [searchParams, showAllPersonas, personaId, sources]);

  useEffect(() => {
    if (selectedIndex !== null && selectedIndex >= sources.length) {
      setSelectedIndex(sources.length > 0 ? Math.max(0, sources.length - 1) : null);
    }
  }, [sources.length, selectedIndex]);

  const togglePlatform = (value: string) => {
    setPlatform((current) => (current === value ? "" : value));
    setSelectedIndex(null);
  };
  const toggleStatus = (value: string) => {
    setStatus((current) => (current === value ? "" : value));
    setSelectedIndex(null);
  };

  return (
    <div className="space-y-6">
      <AddSourceLinkModal open={addLinkOpen} onOpenChange={setAddLinkOpen} personaId={personaId} />
      <QueryError error={sourcesQuery.error ?? statsQuery.error} />

      {statsQuery.isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : stats && stats.total > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          <AllPlatformsCard
            total={stats.total}
            indexed={stats.status_counts["indexed"] ?? 0}
            active={!platform}
            onClick={() => togglePlatform("")}
          />
          {stats.platforms.map((stat) => (
            <PlatformCard
              key={stat.platform}
              stat={stat}
              active={platform === stat.platform}
              onClick={() => togglePlatform(stat.platform)}
            />
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-44 flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Státusz</Label>
          <Select
            value={status || "__all__"}
            onValueChange={(value) => {
              setStatus(value === "__all__" ? "" : value);
              setSelectedIndex(null);
            }}
          >
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Minden státusz" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Minden státusz</SelectItem>
              {SOURCE_STATUS_ORDER.map((statusKey) => (
                <SelectItem key={statusKey} value={statusKey}>
                  {sourceStatusMeta(statusKey).label}
                  {statusCounts[statusKey] !== undefined ? ` (${statusCounts[statusKey]})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex min-w-40 flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Média</Label>
          <Select
            value={media || "__all__"}
            onValueChange={(value) => {
              setMedia(value === "__all__" ? "" : value);
              setSelectedIndex(null);
            }}
          >
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Minden típus" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">Minden típus</SelectItem>
              {MEDIA_FORMAT_ORDER.map((mediaKey) => (
                <SelectItem key={mediaKey} value={mediaKey}>
                  {MEDIA_FORMAT_LABELS[mediaKey]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {sortSourceStatusEntries(statusCounts).map(([statusKey, count]) => (
            <StatusChip
              key={statusKey}
              status={statusKey}
              count={count}
              active={status === statusKey}
              onClick={() => toggleStatus(statusKey)}
            />
          ))}
        </div>
        <div className="relative ml-auto">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Keresés cím/URL..."
            className="w-64 pl-8"
          />
        </div>
        {hasFilter ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus("");
              setPlatform("");
              setMedia("");
              setSearch("");
            }}
          >
            <XIcon className="size-3.5" />
            Szűrők törlése
          </Button>
        ) : null}
      </div>

      <SourceDetailModal
        open={selectedIndex !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedIndex(null);
        }}
        sources={sources}
        selectedIndex={selectedIndex}
        onSelectedIndexChange={setSelectedIndex}
        personaLabels={personaLabels}
      />

      <Card>
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
            <CardTitle className="flex items-baseline gap-2">
              Források
              <span className="text-sm font-normal text-muted-foreground tabular-nums">
                {sources.length}
                {sources.length === 500 ? "+" : ""} találat
              </span>
            </CardTitle>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button type="button" size="sm" variant="outline" onClick={() => setAddLinkOpen(true)}>
                <Link2 className="size-3.5" />
                Link hozzáadása
              </Button>
              {!showAllPersonas ? (
                <>
                  {anyJobRunning && discovery.trackedJob ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => discovery.stopDiscovery.mutate(discovery.trackedJob!.job_id)}
                      disabled={discovery.stopDiscovery.isPending}
                    >
                      Leállítás
                    </Button>
                  ) : null}
                  <DiscoveryLimitButton
                    disabled={
                      anyJobRunning ||
                      discovery.startDiscovery.isPending ||
                      discovery.startProcessing.isPending
                    }
                    isRunning={discoveryActive}
                    onStart={(discoveryLimit) => discovery.startDiscovery.mutate(discoveryLimit)}
                  />
                  <ProcessLimitButton
                    disabled={
                      anyJobRunning ||
                      discovery.startDiscovery.isPending ||
                      discovery.startProcessing.isPending
                    }
                    isRunning={processActive}
                    onStart={(processLimit) => discovery.startProcessing.mutate(processLimit)}
                  />
                </>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Kereséshez és feldolgozáshoz válassz advisort a fejlécben.
                </p>
              )}
            </div>
          </CardHeader>

          {!showAllPersonas &&
          discovery.showProgress &&
          discovery.trackedJob &&
          discovery.isDiscoverOnlyJob ? (
            <SourcePipelineProgress
              personaId={personaId}
              mode="discovery"
              trackedJob={discovery.trackedJob}
              relevantRun={discovery.relevantRun}
              recentEvents={discovery.recentEvents}
              isRunning={discovery.isRunning}
              isFinished={discovery.isFinished}
              onStop={() => discovery.stopDiscovery.mutate(discovery.trackedJob!.job_id)}
              stopPending={discovery.stopDiscovery.isPending}
            />
          ) : null}

          {!showAllPersonas && discovery.showProgress && discovery.trackedJob && discovery.isProcessJob ? (
            <SourcePipelineProgress
              personaId={personaId}
              mode="process"
              trackedJob={discovery.trackedJob}
              relevantRun={discovery.relevantRun}
              recentEvents={discovery.recentEvents}
              isRunning={discovery.isRunning}
              isFinished={discovery.isFinished}
              onStop={() => discovery.stopProcessing.mutate(discovery.trackedJob!.job_id)}
              stopPending={discovery.stopProcessing.isPending}
            />
          ) : null}

          {!showAllPersonas && discovery.startDiscovery.isError ? (
            <p className="border-b px-(--card-spacing) py-2 text-sm text-destructive">
              {discovery.startDiscovery.error instanceof Error
                ? discovery.startDiscovery.error.message
                : "Nem sikerült elindítani a keresést."}
            </p>
          ) : null}

          {!showAllPersonas && discovery.startProcessing.isError ? (
            <p className="border-b px-(--card-spacing) py-2 text-sm text-destructive">
              {discovery.startProcessing.error instanceof Error
                ? discovery.startProcessing.error.message
                : "Nem sikerült elindítani a feldolgozást."}
            </p>
          ) : null}

          <CardContent className="max-h-[38rem] overflow-auto px-0">
            {sourcesQuery.isLoading ? (
              <div className="space-y-2 px-(--card-spacing)">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 rounded-md" />
                ))}
              </div>
            ) : sources.length === 0 ? (
              <p className="px-(--card-spacing) py-8 text-center text-sm text-muted-foreground">
                {hasFilter ? "Nincs a szűrésnek megfelelő forrás." : "Még nincs forrás."}
              </p>
            ) : (
              <table className="w-full table-fixed text-sm">
                <thead className="sticky top-0 z-10 bg-card">
                  <tr className="border-b text-left text-xs text-muted-foreground uppercase tracking-wide">
                    <th className="py-2 pr-2 pl-(--card-spacing) font-medium">Forrás</th>
                    <th className="w-24 py-2 pr-2 font-medium">Státusz</th>
                    {showAllPersonas ? (
                      <th className="w-28 py-2 pr-2 font-medium">Advisor</th>
                    ) : null}
                    <th className="w-20 py-2 pr-(--card-spacing) text-right font-medium">Dátum</th>
                    <th className="w-24 py-2 pr-(--card-spacing) text-right font-medium">Művelet</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source: SourceItem, index: number) => {
                    const isSelected = selectedIndex === index;
                    const dateParts = formatSourceDateStack(source.source_date);
                    return (
                      <tr
                        key={`${source.persona_id}-${source.id}`}
                        className={cn(
                          "cursor-pointer border-b transition-colors last:border-b-0 hover:bg-muted/50",
                          isSelected && "bg-muted"
                        )}
                        onClick={() => setSelectedIndex(index)}
                      >
                        <td className="max-w-0 py-2.5 pr-2 pl-(--card-spacing)">
                          <SourceIdentity
                            title={source.source_title}
                            sourceUrl={source.source_url}
                            sourceType={source.source_type}
                            channelUrl={source.channel_url}
                            subtitle={
                              <>
                                {source.platform}
                                {source.media_format && source.media_format !== "unknown" ? (
                                  <span> · {MEDIA_FORMAT_LABELS[source.media_format]}</span>
                                ) : null}
                                {source.error_message ? (
                                  <span className="text-red-500"> · {source.error_message}</span>
                                ) : null}
                              </>
                            }
                          />
                        </td>
                        <td className="py-2.5 pr-2 whitespace-nowrap">
                          <SourceStatusChip status={source.status} />
                        </td>
                        {showAllPersonas ? (
                          <td className="max-w-0 py-2.5 pr-2">
                            <p
                              className="truncate text-xs text-muted-foreground"
                              title={personaLabels[source.persona_id] ?? source.persona_id}
                            >
                              {personaLabels[source.persona_id] ?? source.persona_id}
                            </p>
                          </td>
                        ) : null}
                        <td className="py-2.5 pr-2 text-right align-middle">
                          {dateParts ? (
                            <div className="leading-tight">
                              <p className="text-xs tabular-nums">{dateParts.date}</p>
                              {dateParts.time ? (
                                <p className="text-[10px] text-muted-foreground tabular-nums">
                                  {dateParts.time}
                                </p>
                              ) : null}
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-2.5 pr-(--card-spacing) align-middle">
                          <SourceRowActions
                            source={source}
                            disabled={anyJobRunning}
                            onProcessStarted={(job) => discovery.trackJob(job.job_id)}
                            onDeleted={() => {
                              if (selectedIndex === index) {
                                setSelectedIndex(null);
                              } else if (selectedIndex !== null && index < selectedIndex) {
                                setSelectedIndex(selectedIndex - 1);
                              }
                            }}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
    </div>
  );
}
