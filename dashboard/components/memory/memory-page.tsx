"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChannelTypeIconMini,
  resolveSourceIconType,
} from "@/components/channels/channel-type-icon";
import { PlatformFilterButton } from "@/components/shared/platform-icon";
import { fetchUnitStats, fetchUnits } from "@/lib/api/client";
import type { KnowledgeUnitItem, UnitStats } from "@/lib/api/types";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

const CONTENT_TYPE_FILTERS = [
  "principle",
  "framework",
  "process",
  "story",
  "quote",
  "step_by_step",
  "example",
  "case_study",
  "diagnostic_logic",
] as const;

const CONFIDENCE_FILTERS = ["strong", "medium", "weak"] as const;

type ContentTypeFilter = (typeof CONTENT_TYPE_FILTERS)[number];
type ConfidenceFilter = (typeof CONFIDENCE_FILTERS)[number];

type SelectedContentType = ContentTypeFilter | (string & {});

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      type="button"
      size="xs"
      variant={active ? "default" : "outline"}
      onClick={onClick}
      aria-pressed={active}
    >
      {label}
    </Button>
  );
}

function StatItem({
  label,
  value,
  active,
  onClick,
}: {
  label: string;
  value: number;
  active?: boolean;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="font-medium tabular-nums text-foreground">{value.toLocaleString("hu-HU")}</span>
      <span>{label}</span>
    </>
  );

  if (!onClick) {
    return <span className="inline-flex items-center gap-1">{content}</span>;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded px-1 transition-colors hover:bg-muted/80 ${
        active ? "bg-muted text-foreground" : ""
      }`}
    >
      {content}
    </button>
  );
}

function StatDivider() {
  return <span className="text-border/80" aria-hidden="true">·</span>;
}

function MemoryPlatformFilter({
  byPlatform,
  platform,
  onPlatform,
}: {
  byPlatform: Record<string, number>;
  platform: string;
  onPlatform: (platform: string) => void;
}) {
  const platforms = Object.entries(byPlatform).sort(([, a], [, b]) => b - a);
  if (!platforms.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-md border bg-muted/20 px-3 py-1.5">
      <span className="mr-0.5 text-xs text-muted-foreground">Platform</span>
      {platforms.map(([name, count]) => (
        <PlatformFilterButton
          key={name}
          platform={name}
          count={count}
          active={platform === name}
          onClick={() => onPlatform(name)}
        />
      ))}
    </div>
  );
}

function MemoryStatsBar({
  stats,
  contentType,
  confidence,
  duplicatesOnly,
  onContentType,
  onConfidence,
  onDuplicatesOnly,
}: {
  stats: UnitStats;
  contentType: SelectedContentType | "";
  confidence: ConfidenceFilter | "";
  duplicatesOnly: boolean;
  onContentType: (type: string) => void;
  onConfidence: (level: ConfidenceFilter) => void;
  onDuplicatesOnly: () => void;
}) {
  const topTypes = Object.entries(stats.by_content_type)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
      <StatItem label="unit" value={stats.total} />
      <StatDivider />
      <StatItem label="indexelt forrás" value={stats.indexed_sources} />
      <StatDivider />
      <StatItem label="forrás unitokkal" value={stats.sources_with_units} />
      {CONFIDENCE_FILTERS.map((level) =>
        stats.by_confidence[level] ? (
          <span key={level} className="inline-flex items-center gap-3">
            <StatDivider />
            <StatItem
              label={level}
              value={stats.by_confidence[level]}
              active={confidence === level}
              onClick={() => onConfidence(level)}
            />
          </span>
        ) : null
      )}
      {stats.duplicates ? (
        <>
          <StatDivider />
          <StatItem
            label="duplikátum"
            value={stats.duplicates}
            active={duplicatesOnly}
            onClick={onDuplicatesOnly}
          />
        </>
      ) : null}
      {topTypes.length ? (
        <>
          <StatDivider />
          {topTypes.map(([type, count], index) => (
            <span key={type} className="inline-flex items-center gap-3">
              {index > 0 ? <StatDivider /> : null}
              <StatItem
                label={type}
                value={count}
                active={contentType === type}
                onClick={() => onContentType(type)}
              />
            </span>
          ))}
        </>
      ) : null}
    </div>
  );
}

function SourceAttribution({
  sourceTitle,
  sourceUrl,
  sourceDate,
  sourceType = "",
  channelUrl,
}: {
  sourceTitle: string | null | undefined;
  sourceUrl: string | null | undefined;
  sourceDate?: string | null;
  sourceType?: string;
  channelUrl?: string | null;
}) {
  const label = sourceTitle?.trim() || sourceUrl?.trim();
  if (!label) {
    return <p className="text-xs text-muted-foreground">Forrás: ismeretlen</p>;
  }

  const iconType = resolveSourceIconType(sourceType, sourceUrl ?? "", channelUrl ?? "");

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 border-t pt-2 text-xs text-muted-foreground">
      <span className="font-medium text-foreground/70">Forrás:</span>
      <span className="inline-flex items-center gap-1.5">
        <ChannelTypeIconMini type={iconType} />
        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="font-medium text-primary underline-offset-2 hover:underline"
          >
            {label}
          </a>
        ) : (
          <span className="font-medium text-foreground/80">{label}</span>
        )}
      </span>
      {sourceDate ? <span>· {sourceDate.slice(0, 10)}</span> : null}
    </div>
  );
}

function UnitCard({ unit }: { unit: KnowledgeUnitItem }) {
  return (
    <div className="rounded-md border p-3 text-sm">
      <div className="flex flex-wrap gap-2">
        <Badge variant="secondary">{unit.content_type}</Badge>
        <Badge>{unit.confidence}</Badge>
        {unit.duplicate_of ? <Badge variant="outline">dup #{unit.duplicate_of}</Badge> : null}
      </div>
      <p className="mt-2">{unit.chunk_text.slice(0, 280)}...</p>
      <SourceAttribution
        sourceTitle={unit.source_title}
        sourceUrl={unit.source_url}
        sourceType={unit.source_type}
        channelUrl={unit.channel_url}
      />
    </div>
  );
}

export function MemoryPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [platform, setPlatform] = useState("");
  const [contentType, setContentType] = useState<SelectedContentType | "">("");
  const [confidence, setConfidence] = useState<ConfidenceFilter | "">("");
  const [duplicatesOnly, setDuplicatesOnly] = useState(false);
  const [unitTextFilter, setUnitTextFilter] = useState("");

  const hasUnitFilters = Boolean(
    platform || contentType || confidence || duplicatesOnly || unitTextFilter
  );

  const statsQuery = useQuery({
    queryKey: ["unit-stats", personaId],
    queryFn: () => fetchUnitStats(personaId),
    enabled: Boolean(personaId),
  });

  const unitsQuery = useQuery({
    queryKey: ["units", personaId, platform, contentType, confidence, duplicatesOnly],
    queryFn: () =>
      fetchUnits(
        personaId,
        Object.fromEntries(
          Object.entries({
            limit: "100",
            platform,
            content_type: contentType,
            confidence,
            duplicates_only: duplicatesOnly ? "true" : "",
          }).filter(([, value]) => Boolean(value))
        )
      ),
    enabled: Boolean(personaId),
  });

  const filteredUnits = useMemo(() => {
    const units = unitsQuery.data ?? [];
    const needle = unitTextFilter.trim().toLowerCase();
    if (!needle) return units;
    return units.filter(
      (unit) =>
        unit.chunk_text.toLowerCase().includes(needle) ||
        (unit.source_title?.toLowerCase().includes(needle) ?? false)
    );
  }, [unitsQuery.data, unitTextFilter]);

  const clearUnitFilters = () => {
    setPlatform("");
    setContentType("");
    setConfidence("");
    setDuplicatesOnly(false);
    setUnitTextFilter("");
  };

  const togglePlatform = (name: string) => {
    setPlatform((current) => (current === name ? "" : name));
  };

  const toggleContentType = (type: string) => {
    setContentType((current) => (current === type ? "" : type));
  };

  const toggleConfidence = (level: ConfidenceFilter) => {
    setConfidence((current) => (current === level ? "" : level));
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Memória"
        description="Knowledge unit böngésző és statisztika."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={statsQuery.error ?? unitsQuery.error} />

      {statsQuery.data ? (
        <>
          <MemoryStatsBar
            stats={statsQuery.data}
            contentType={contentType}
            confidence={confidence}
            duplicatesOnly={duplicatesOnly}
            onContentType={toggleContentType}
            onConfidence={toggleConfidence}
            onDuplicatesOnly={() => setDuplicatesOnly((current) => !current)}
          />
          <MemoryPlatformFilter
            byPlatform={statsQuery.data.by_platform ?? {}}
            platform={platform}
            onPlatform={togglePlatform}
          />
        </>
      ) : statsQuery.isPending ? (
        <div className="space-y-2">
          <div className="h-9 animate-pulse rounded-md border bg-muted/30" />
          <div className="h-9 animate-pulse rounded-md border bg-muted/20" />
        </div>
      ) : null}

      <Card>
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>Knowledge unitok</CardTitle>
            {hasUnitFilters ? (
              <Button type="button" size="xs" variant="ghost" onClick={clearUnitFilters}>
                Szűrők törlése
              </Button>
            ) : null}
          </div>
          <div className="space-y-3 text-sm">
            <input
              value={unitTextFilter}
              onChange={(e) => setUnitTextFilter(e.target.value)}
              placeholder="Keresés szövegben vagy forráscímben..."
              className="w-full max-w-md rounded-md border bg-background px-3 py-2 text-sm"
            />
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Típus</p>
              <div className="flex flex-wrap gap-1.5">
                {CONTENT_TYPE_FILTERS.map((type) => (
                  <FilterChip
                    key={type}
                    label={type}
                    active={contentType === type}
                    onClick={() => toggleContentType(type)}
                  />
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Confidence</p>
              <div className="flex flex-wrap gap-1.5">
                {CONFIDENCE_FILTERS.map((level) => (
                  <FilterChip
                    key={level}
                    label={level}
                    active={confidence === level}
                    onClick={() => toggleConfidence(level)}
                  />
                ))}
                <FilterChip
                  label="duplikátumok"
                  active={duplicatesOnly}
                  onClick={() => setDuplicatesOnly((current) => !current)}
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {filteredUnits.length} megjelenítve
            {unitsQuery.data && filteredUnits.length !== unitsQuery.data.length
              ? ` (${unitsQuery.data.length} betöltve)`
              : statsQuery.data
                ? ` / ${statsQuery.data.total.toLocaleString("hu-HU")} összesen`
                : null}
          </p>
          {filteredUnits.length ? (
            filteredUnits.map((unit) => <UnitCard key={unit.id} unit={unit} />)
          ) : (
            <p className="text-sm text-muted-foreground">
              {hasUnitFilters ? "Nincs találat a szűrőkkel." : "Még nincs indexelt unit."}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
