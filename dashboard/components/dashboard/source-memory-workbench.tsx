"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Cancel as XIcon } from "@/lib/icons";

import { QueryError } from "@/components/shared/api-guard";
import { PlatformFilterButton } from "@/components/shared/platform-icon";
import { SourceIdentity } from "@/components/shared/source-identity";
import { SourceStatusChip } from "@/components/shared/source-status-chip";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchAllSourceStats,
  fetchAllSourcesWithMemory,
  fetchSourceStats,
  fetchSourcesWithMemory,
} from "@/lib/api/client";
import type { SourceWithMemoryItem } from "@/lib/api/types";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { SOURCE_ACTIVE_STATUSES } from "@/lib/source-status";
import { cn } from "@/lib/utils";

import { SourceDetailPanel } from "./source-detail-panel";

type SmartFilter = "" | "attention" | "active" | "with_memory" | "without_memory";
type SelectedSource = { id: number; personaId: string };

const SMART_FILTERS: { id: SmartFilter; label: string }[] = [
  { id: "", label: "Mind" },
  { id: "attention", label: "Figyelmet kér" },
  { id: "active", label: "Fut / aktuális" },
  { id: "with_memory", label: "Memóriával" },
  { id: "without_memory", label: "Memória nélkül" },
];

function memorySummary(item: SourceWithMemoryItem): string {
  if (item.unit_count === 0) return "nincs memória";
  const parts = [`${item.unit_count} unit`];
  if (item.strong_count > 0) parts.push(`${item.strong_count} strong`);
  if (item.duplicate_count > 0) parts.push(`${item.duplicate_count} dup`);
  return parts.join(" · ");
}

export function SourceMemoryWorkbench({
  personaId,
  showAllPersonas,
}: {
  personaId: string;
  showAllPersonas: boolean;
}) {
  const { personas } = usePersonaOptions();
  const personaLabels = Object.fromEntries(
    personas.map((persona) => [persona.persona_id, persona.display_name])
  );
  const [smartFilter, setSmartFilter] = useState<SmartFilter>("");
  const [platform, setPlatform] = useState("");
  const [search, setSearch] = useState("");
  const [selectedSource, setSelectedSource] = useState<SelectedSource | null>(null);

  const statsQuery = useQuery({
    queryKey: ["source-stats", personaId],
    queryFn: () => (showAllPersonas ? fetchAllSourceStats() : fetchSourceStats(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
  });

  const params: Record<string, string> = { limit: "300" };
  if (search) params.search = search;
  if (platform) params.platform = platform;
  if (smartFilter === "attention") params.needs_attention = "true";
  if (smartFilter === "with_memory") params.has_memory = "true";
  if (smartFilter === "without_memory") params.has_memory = "false";

  const sourcesQuery = useQuery({
    queryKey: ["sources-with-memory", personaId, smartFilter, platform, search],
    queryFn: () =>
      showAllPersonas
        ? fetchAllSourcesWithMemory(params)
        : fetchSourcesWithMemory(personaId, params),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 15000,
  });

  const items = useMemo(() => {
    const data = sourcesQuery.data ?? [];
    if (smartFilter === "active") {
      return data.filter((item) => SOURCE_ACTIVE_STATUSES.includes(item.status));
    }
    return data;
  }, [sourcesQuery.data, smartFilter]);

  const hasFilter = Boolean(smartFilter || platform || search);
  const selected =
    items.find(
      (item) =>
        selectedSource?.id === item.id && selectedSource.personaId === item.persona_id
    ) ?? null;
  const detailPersonaId = selected?.persona_id ?? personaId;

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Források és memória</CardTitle>
          <span className="text-xs tabular-nums text-muted-foreground">
            {items.length}
            {items.length === 300 ? "+" : ""} találat
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {SMART_FILTERS.map((filter) => (
            <Button
              key={filter.id || "all"}
              type="button"
              size="xs"
              variant={smartFilter === filter.id ? "default" : "outline"}
              onClick={() => setSmartFilter(filter.id)}
            >
              {filter.label}
            </Button>
          ))}
          <div className="relative ml-auto">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Keresés cím/URL..."
              className="w-56 pl-8"
            />
          </div>
          {hasFilter ? (
            <Button
              variant="ghost"
              size="xs"
              onClick={() => {
                setSmartFilter("");
                setPlatform("");
                setSearch("");
              }}
            >
              <XIcon className="size-3.5" />
              Törlés
            </Button>
          ) : null}
        </div>
        {statsQuery.data && statsQuery.data.platforms.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {statsQuery.data.platforms.map((stat) => (
              <PlatformFilterButton
                key={stat.platform}
                platform={stat.platform}
                count={stat.total}
                active={platform === stat.platform}
                onClick={() =>
                  setPlatform((current) => (current === stat.platform ? "" : stat.platform))
                }
              />
            ))}
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="px-0">
        <QueryError error={sourcesQuery.error} />
        <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
          <div className="max-h-[36rem] overflow-auto pl-(--card-spacing)">
            {sourcesQuery.isLoading ? (
              <div className="space-y-2 pr-(--card-spacing)">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 rounded-md" />
                ))}
              </div>
            ) : items.length === 0 ? (
              <p className="py-8 pr-(--card-spacing) text-center text-sm text-muted-foreground">
                {hasFilter ? "Nincs a szűrésnek megfelelő forrás." : "Még nincs forrás."}
              </p>
            ) : (
              <table className="w-full table-fixed text-sm">
                <colgroup>
                  <col />
                  <col className="w-[18%]" />
                  {showAllPersonas ? <col className="w-[14%]" /> : null}
                  <col className="w-[22%]" />
                  <col className="w-[14%]" />
                </colgroup>
                <thead className="sticky top-0 z-10 bg-card">
                  <tr className="border-b text-left text-xs text-muted-foreground uppercase tracking-wide">
                    <th className="py-2 pr-2 font-medium">Forrás</th>
                    <th className="py-2 pr-2 font-medium">Státusz</th>
                    {showAllPersonas ? <th className="py-2 pr-2 font-medium">Advisor</th> : null}
                    <th className="py-2 pr-2 font-medium">Memória</th>
                    <th className="py-2 pr-(--card-spacing) text-right font-medium">Dátum</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const isSelected =
                      selectedSource?.id === item.id &&
                      selectedSource.personaId === item.persona_id;
                    return (
                      <tr
                        key={`${item.persona_id}-${item.id}`}
                        className={cn(
                          "cursor-pointer border-b transition-colors last:border-b-0 hover:bg-muted/50",
                          isSelected && "bg-muted"
                        )}
                        onClick={() =>
                          setSelectedSource({ id: item.id, personaId: item.persona_id })
                        }
                      >
                        <td className="max-w-0 py-2.5 pr-2">
                          <SourceIdentity
                            title={item.source_title}
                            sourceUrl={item.source_url}
                            sourceType={item.source_type}
                            channelUrl={item.channel_url}
                            subtitle={
                              <>
                                {item.platform}
                                {item.error_message ? (
                                  <span className="text-red-500"> · {item.error_message}</span>
                                ) : null}
                              </>
                            }
                          />
                        </td>
                        <td className="py-2.5 pr-2 whitespace-nowrap">
                          <div className="flex items-center gap-1.5">
                            <SourceStatusChip status={item.status} />
                            {item.needs_attention ? (
                              <span
                                className="size-1.5 rounded-full bg-red-500"
                                title="Figyelmet igényel"
                                aria-hidden
                              />
                            ) : null}
                          </div>
                        </td>
                        {showAllPersonas ? (
                          <td className="max-w-0 py-2.5 pr-2">
                            <p
                              className="truncate text-xs text-muted-foreground"
                              title={personaLabels[item.persona_id] ?? item.persona_id}
                            >
                              {personaLabels[item.persona_id] ?? item.persona_id}
                            </p>
                          </td>
                        ) : null}
                        <td className="py-2.5 pr-2 text-xs whitespace-nowrap text-muted-foreground">
                          {memorySummary(item)}
                        </td>
                        <td className="py-2.5 pr-(--card-spacing) text-right text-xs whitespace-nowrap text-muted-foreground tabular-nums">
                          {item.source_date ? item.source_date.slice(0, 10) : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
          <div className="self-start pr-(--card-spacing) xl:sticky xl:top-6">
            <SourceDetailPanel
              personaId={detailPersonaId}
              sourceId={selected?.id ?? null}
              summary={selected}
              personaLabel={
                selected
                  ? (personaLabels[selected.persona_id] ?? selected.persona_id)
                  : undefined
              }
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
