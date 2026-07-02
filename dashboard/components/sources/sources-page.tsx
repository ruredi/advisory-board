"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Layers, Search, X as XIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChannelTypeIcon,
  ChannelTypeIconMini,
  resolveSourceIconType,
} from "@/components/channels/channel-type-icon";
import { fetchSource, fetchSources, fetchSourceStats, patchSource } from "@/lib/api/client";
import type { SourceItem, SourcePlatformStat } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";
import { cn } from "@/lib/utils";

const STATUS_META: Record<string, { label: string; chipClass: string; dotClass: string }> = {
  pending: {
    label: "várakozó",
    chipClass: "bg-amber-500/10 text-amber-700 border-amber-500/25 dark:text-amber-400",
    dotClass: "bg-amber-500",
  },
  fetching: {
    label: "letöltés",
    chipClass: "bg-blue-500/10 text-blue-700 border-blue-500/25 dark:text-blue-400",
    dotClass: "bg-blue-500 animate-pulse",
  },
  fetched: {
    label: "letöltve",
    chipClass: "bg-blue-500/10 text-blue-700 border-blue-500/25 dark:text-blue-400",
    dotClass: "bg-blue-500",
  },
  processing: {
    label: "feldolgozás",
    chipClass: "bg-sky-500/10 text-sky-700 border-sky-500/25 dark:text-sky-400",
    dotClass: "bg-sky-500 animate-pulse",
  },
  processed: {
    label: "feldolgozva",
    chipClass: "bg-sky-500/10 text-sky-700 border-sky-500/25 dark:text-sky-400",
    dotClass: "bg-sky-500",
  },
  extracting: {
    label: "kinyerés",
    chipClass: "bg-violet-500/10 text-violet-700 border-violet-500/25 dark:text-violet-400",
    dotClass: "bg-violet-500 animate-pulse",
  },
  indexed: {
    label: "indexelve",
    chipClass: "bg-emerald-500/10 text-emerald-700 border-emerald-500/25 dark:text-emerald-400",
    dotClass: "bg-emerald-500",
  },
  failed: {
    label: "hibás",
    chipClass: "bg-red-500/10 text-red-700 border-red-500/25 dark:text-red-400",
    dotClass: "bg-red-500",
  },
  skipped: {
    label: "kihagyva",
    chipClass: "bg-zinc-500/10 text-zinc-600 border-zinc-500/25 dark:text-zinc-400",
    dotClass: "bg-zinc-400",
  },
};

const STATUS_ORDER = [
  "indexed",
  "pending",
  "fetching",
  "fetched",
  "processing",
  "processed",
  "extracting",
  "failed",
  "skipped",
];

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

function statusMeta(status: string) {
  return (
    STATUS_META[status] ?? {
      label: status,
      chipClass: "bg-muted text-muted-foreground border-border",
      dotClass: "bg-muted-foreground",
    }
  );
}

function sortStatusEntries(counts: Record<string, number>): [string, number][] {
  return Object.entries(counts).sort(([a], [b]) => {
    const ia = STATUS_ORDER.indexOf(a);
    const ib = STATUS_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

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
  const meta = statusMeta(status);
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all",
        meta.chipClass,
        active
          ? "ring-2 ring-primary/40 ring-offset-1 ring-offset-background"
          : "opacity-80 hover:opacity-100"
      )}
    >
      <span className={cn("size-1.5 rounded-full", meta.dotClass)} aria-hidden />
      {meta.label}
      <span className="tabular-nums">{count}</span>
    </button>
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
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex flex-col gap-2 rounded-xl bg-card p-3 text-left ring-1 transition-all",
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
    </button>
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
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex flex-col gap-2 rounded-xl bg-card p-3 text-left ring-1 transition-all",
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
    </button>
  );
}

export function SourcesPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [status, setStatus] = useState("");
  const [platform, setPlatform] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const statsQuery = useQuery({
    queryKey: ["source-stats", personaId],
    queryFn: () => fetchSourceStats(personaId),
    enabled: Boolean(personaId),
  });

  const sourcesQuery = useQuery({
    queryKey: ["sources", personaId, status, platform, search],
    queryFn: () =>
      fetchSources(
        personaId,
        Object.fromEntries(
          Object.entries({ status, platform, search, limit: "500" }).filter(([, value]) =>
            Boolean(value)
          )
        )
      ),
    enabled: Boolean(personaId),
  });

  const detailQuery = useQuery({
    queryKey: ["source", personaId, selectedId],
    queryFn: () => fetchSource(personaId, selectedId!),
    enabled: selectedId !== null,
  });

  const patchMutation = useMutation({
    mutationFn: ({ sourceId, nextStatus }: { sourceId: number; nextStatus: string }) =>
      patchSource(personaId, sourceId, nextStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources", personaId] });
      queryClient.invalidateQueries({ queryKey: ["source-stats", personaId] });
      if (selectedId) queryClient.invalidateQueries({ queryKey: ["source", personaId, selectedId] });
    },
  });

  const stats = statsQuery.data;

  // A státusz chipek a kiválasztott platform bontását mutatják, ha van szűrés.
  const statusCounts = useMemo(() => {
    if (!stats) return {};
    if (!platform) return stats.status_counts;
    return stats.platforms.find((p) => p.platform === platform)?.status_counts ?? {};
  }, [stats, platform]);

  const sources = sourcesQuery.data ?? [];
  const detail = detailQuery.data;
  const hasFilter = Boolean(status || platform || search);

  const togglePlatform = (value: string) => {
    setPlatform((current) => (current === value ? "" : value));
    setSelectedId(null);
  };
  const toggleStatus = (value: string) => {
    setStatus((current) => (current === value ? "" : value));
    setSelectedId(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Források"
        description="Source lista platformonként, státusz kezelés, részletek."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

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

      <div className="flex flex-wrap items-center gap-2">
        {sortStatusEntries(statusCounts).map(([statusKey, count]) => (
          <StatusChip
            key={statusKey}
            status={statusKey}
            count={count}
            active={status === statusKey}
            onClick={() => toggleStatus(statusKey)}
          />
        ))}
        <div className="relative ml-auto">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Keresés cím/URL..."
            className="w-64 rounded-md border bg-background py-2 pr-3 pl-8 text-sm"
          />
        </div>
        {hasFilter ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus("");
              setPlatform("");
              setSearch("");
            }}
          >
            <XIcon className="size-3.5" />
            Szűrők törlése
          </Button>
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-baseline gap-2">
              Források
              <span className="text-sm font-normal text-muted-foreground tabular-nums">
                {sources.length}
                {sources.length === 500 ? "+" : ""} találat
              </span>
            </CardTitle>
          </CardHeader>
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
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10 bg-card">
                  <tr className="border-b text-left text-xs text-muted-foreground uppercase tracking-wide">
                    <th className="py-2 pr-2 pl-(--card-spacing) font-medium">Forrás</th>
                    <th className="py-2 pr-2 font-medium">Státusz</th>
                    <th className="py-2 pr-(--card-spacing) text-right font-medium">Dátum</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source: SourceItem) => {
                    const meta = statusMeta(source.status);
                    const iconType = resolveSourceIconType(
                      source.source_type,
                      source.source_url,
                      source.channel_url ?? ""
                    );
                    return (
                      <tr
                        key={source.id}
                        className={cn(
                          "cursor-pointer border-b transition-colors last:border-b-0 hover:bg-muted/50",
                          selectedId === source.id && "bg-muted"
                        )}
                        onClick={() => setSelectedId(source.id)}
                      >
                        <td className="max-w-0 py-2.5 pr-2 pl-(--card-spacing)">
                          <div className="flex items-center gap-2.5">
                            <ChannelTypeIconMini type={iconType} />
                            <div className="min-w-0">
                              <p className="truncate font-medium">
                                {source.source_title || source.source_url}
                              </p>
                              <p className="truncate text-xs text-muted-foreground">
                                {source.platform}
                                {source.error_message ? (
                                  <span className="text-red-500"> · {source.error_message}</span>
                                ) : null}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="py-2.5 pr-2 whitespace-nowrap">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
                              meta.chipClass
                            )}
                          >
                            <span
                              className={cn("size-1.5 rounded-full", meta.dotClass)}
                              aria-hidden
                            />
                            {meta.label}
                          </span>
                        </td>
                        <td className="py-2.5 pr-(--card-spacing) text-right text-xs whitespace-nowrap text-muted-foreground tabular-nums">
                          {source.source_date ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card className="self-start xl:sticky xl:top-6">
          <CardHeader>
            <CardTitle>Részletek</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {!selectedId ? (
              <p className="text-muted-foreground">Válassz forrást a listából.</p>
            ) : null}
            {selectedId && detailQuery.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4 rounded" />
                <Skeleton className="h-4 w-1/2 rounded" />
                <Skeleton className="h-24 rounded" />
              </div>
            ) : null}
            {detail ? (
              <>
                <div className="flex items-start gap-3">
                  <ChannelTypeIcon
                    type={resolveSourceIconType(
                      detail.source_type,
                      detail.source_url,
                      detail.channel_url ?? ""
                    )}
                  />
                  <div className="min-w-0 space-y-1">
                    <p className="font-medium leading-snug">
                      {detail.source_title || detail.source_url}
                    </p>
                    <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {detail.platform}
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-medium",
                          statusMeta(detail.status).chipClass
                        )}
                      >
                        <span
                          className={cn(
                            "size-1.5 rounded-full",
                            statusMeta(detail.status).dotClass
                          )}
                          aria-hidden
                        />
                        {statusMeta(detail.status).label}
                      </span>
                    </p>
                  </div>
                </div>

                <a
                  href={detail.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex max-w-full items-center gap-1.5 text-xs text-primary underline underline-offset-2"
                >
                  <ExternalLink className="size-3.5 shrink-0" />
                  <span className="truncate">{detail.source_url}</span>
                </a>

                {detail.error_message ? (
                  <div className="rounded-md border border-red-500/25 bg-red-500/10 p-2.5 text-xs text-red-700 dark:text-red-400">
                    {detail.error_message}
                  </div>
                ) : null}

                <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <dt className="text-muted-foreground">Knowledge unitok</dt>
                  <dd className="text-right font-medium tabular-nums">{detail.unit_count}</dd>
                  {detail.source_date ? (
                    <>
                      <dt className="text-muted-foreground">Publikálva</dt>
                      <dd className="text-right tabular-nums">{detail.source_date}</dd>
                    </>
                  ) : null}
                  {detail.processed_at ? (
                    <>
                      <dt className="text-muted-foreground">Feldolgozva</dt>
                      <dd className="text-right tabular-nums">
                        {formatDateTime(detail.processed_at)}
                      </dd>
                    </>
                  ) : null}
                </dl>

                <div className="flex flex-wrap gap-2">
                  {detail.status !== "pending" ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={patchMutation.isPending}
                      onClick={() =>
                        patchMutation.mutate({ sourceId: selectedId!, nextStatus: "pending" })
                      }
                    >
                      Újra sorba állít
                    </Button>
                  ) : null}
                  {detail.status !== "skipped" ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={patchMutation.isPending}
                      onClick={() =>
                        patchMutation.mutate({ sourceId: selectedId!, nextStatus: "skipped" })
                      }
                    >
                      Kihagy
                    </Button>
                  ) : null}
                </div>

                {detail.processed_text ? (
                  <pre className="max-h-64 overflow-auto rounded-md border bg-muted/30 p-2.5 text-xs whitespace-pre-wrap">
                    {detail.processed_text}
                  </pre>
                ) : null}
              </>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
