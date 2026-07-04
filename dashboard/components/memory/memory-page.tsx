"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";

import { QueryError } from "@/components/shared/api-guard";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ChannelTypeIconMini,
  resolveSourceIconType,
} from "@/components/channels/channel-type-icon";
import { PlatformFilterButton } from "@/components/shared/platform-icon";
import {
  ALL_PERSONAS,
  fetchAllUnitStats,
  fetchAllUnits,
  fetchUnitStats,
  fetchUnits,
  searchMemory,
} from "@/lib/api/client";
import type { KnowledgeUnitItem, SearchHit, UnitStats } from "@/lib/api/types";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";
import { ChevronDown, ExternalLink } from "@/lib/icons";
import { cn } from "@/lib/utils";

const PREVIEW_LENGTH = 280;

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
    <Button
      type="button"
      variant="ghost"
      size="xs"
      onClick={onClick}
      className={cn(
        "h-auto gap-1 px-1 font-normal text-muted-foreground hover:text-muted-foreground",
        active && "bg-muted text-foreground"
      )}
    >
      {content}
    </Button>
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
  sourceId,
  sourceTitle,
  sourceUrl,
  sourceDate,
  sourceType = "",
  channelUrl,
}: {
  sourceId: number;
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
        <Link
          href={`/sources?source=${sourceId}`}
          className="font-medium text-primary underline-offset-2 hover:underline"
        >
          {label}
        </Link>
        {sourceUrl ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            title="Eredeti anyag megnyitása"
            className="inline-flex items-center text-primary/70 hover:text-primary"
          >
            <ExternalLink className="size-3.5" />
            <span className="sr-only">Eredeti anyag</span>
          </a>
        ) : null}
      </span>
      {sourceDate ? <span>· {sourceDate.slice(0, 10)}</span> : null}
    </div>
  );
}

function UnitMetadata({ unit }: { unit: KnowledgeUnitItem }) {
  const quoteItems = unit.quotes ?? [];
  return (
    <div className="mt-2 space-y-2 border-t pt-2 text-xs text-muted-foreground">
      <div className="flex flex-wrap gap-1.5">
        <Badge variant="outline">{unit.evidence_type}</Badge>
        <Badge variant="outline">prio {unit.retrieval_priority}</Badge>
        {!unit.is_new_information ? <Badge variant="outline">ismétlődő</Badge> : null}
      </div>
      {unit.frameworks.length ? (
        <p>
          <span className="font-medium text-foreground/70">Frameworks: </span>
          {unit.frameworks.join(", ")}
        </p>
      ) : null}
      {unit.processes.length ? (
        <p>
          <span className="font-medium text-foreground/70">Processes: </span>
          {unit.processes.join(", ")}
        </p>
      ) : null}
      {unit.steps.length ? (
        <ul className="list-disc pl-4">
          {unit.steps.slice(0, 5).map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
      ) : null}
      {quoteItems.length ? (
        <div className="space-y-1.5">
          {quoteItems.map((quote, index) => {
            const text = String(quote.text ?? "");
            const link = String(quote.source_link ?? quote.source_url ?? "");
            return (
              <blockquote key={`${index}-${text.slice(0, 24)}`} className="rounded border bg-muted/20 p-2 italic">
                “{text}”
                {link ? (
                  <a
                    href={link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block not-italic text-primary underline-offset-2 hover:underline"
                  >
                    Forrás link
                    {quote.start_seconds != null ? ` · ${Math.floor(Number(quote.start_seconds))}s` : ""}
                  </a>
                ) : null}
              </blockquote>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function SearchHitCard({ hit }: { hit: SearchHit }) {
  return (
    <div className="rounded-md border p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{hit.content_type}</Badge>
        <Badge>{hit.confidence}</Badge>
        <Badge variant="outline">score {(hit.score * 100).toFixed(0)}%</Badge>
      </div>
      <p className="mt-2 whitespace-pre-wrap">{hit.chunk_text}</p>
      <UnitMetadata
        unit={{
          id: hit.unit_id,
          persona_id: "",
          source_id: 0,
          content_type: hit.content_type,
          chunk_text: hit.chunk_text,
          confidence: hit.confidence,
          is_new_information: hit.is_new_information,
          duplicate_of: null,
          source_title: hit.source_title,
          source_url: hit.source_url,
          source_type: hit.source_type,
          channel_url: hit.channel_url,
          frameworks: hit.frameworks,
          processes: hit.processes,
          steps: hit.steps,
          quotes: hit.quotes,
          evidence_type: hit.evidence_type,
          retrieval_priority: hit.retrieval_priority,
        }}
      />
      <SourceAttribution
        sourceId={0}
        sourceTitle={hit.source_title}
        sourceUrl={hit.source_url}
        sourceDate={hit.source_date}
        sourceType={hit.source_type}
        channelUrl={hit.channel_url}
      />
    </div>
  );
}

function SemanticSearchPanel({
  personaId,
  disabled,
}: {
  personaId: string;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [contextPack, setContextPack] = useState(false);
  const searchMutation = useMutation({
    mutationFn: () => searchMemory(personaId, query.trim(), contextPack),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Szemantikus keresés</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {disabled ? (
          <p className="text-sm text-muted-foreground">
            Válassz egy advisort a szemantikus kereséshez.
          </p>
        ) : (
          <>
        <div className="flex flex-wrap gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Kérdés vagy keresőkifejezés..."
            className="max-w-md"
            onKeyDown={(event) => {
              if (event.key === "Enter" && query.trim()) {
                searchMutation.mutate();
              }
            }}
          />
          <Button
            type="button"
            disabled={!query.trim() || searchMutation.isPending}
            onClick={() => searchMutation.mutate()}
          >
            Keresés
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="context-pack"
            checked={contextPack}
            onCheckedChange={(checked) => setContextPack(checked === true)}
          />
          <Label htmlFor="context-pack" className="text-sm font-normal">
            Context pack generálása
          </Label>
        </div>
        {searchMutation.error ? <QueryError error={searchMutation.error} /> : null}
        {searchMutation.data?.hits.length ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{searchMutation.data.hits.length} találat</p>
            {searchMutation.data.hits.map((hit) => (
              <SearchHitCard key={hit.unit_id} hit={hit} />
            ))}
          </div>
        ) : null}
        {searchMutation.data?.context_pack ? (
          <details className="rounded-md border bg-muted/20 p-2 text-xs">
            <summary className="cursor-pointer font-medium">Context pack</summary>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap">
              {searchMutation.data.context_pack}
            </pre>
          </details>
        ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function UnitCard({
  unit,
  personaLabel,
}: {
  unit: KnowledgeUnitItem;
  personaLabel?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLong = unit.chunk_text.length > PREVIEW_LENGTH;
  const preview = isLong ? `${unit.chunk_text.slice(0, PREVIEW_LENGTH)}…` : unit.chunk_text;

  const toggleExpanded = () => {
    if (isLong) setExpanded((current) => !current);
  };

  return (
    <div
      className={cn(
        "rounded-md border p-3 text-sm transition-colors",
        expanded && "bg-muted/20"
      )}
    >
      <div
        className={cn(isLong && "cursor-pointer")}
        role={isLong ? "button" : undefined}
        tabIndex={isLong ? 0 : undefined}
        aria-expanded={isLong ? expanded : undefined}
        onClick={toggleExpanded}
        onKeyDown={(event) => {
          if (!isLong) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggleExpanded();
          }
        }}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex flex-wrap gap-2">
            {personaLabel ? <Badge variant="outline">{personaLabel}</Badge> : null}
            <Badge variant="secondary">{unit.content_type}</Badge>
            <Badge>{unit.confidence}</Badge>
            {unit.duplicate_of ? <Badge variant="outline">dup #{unit.duplicate_of}</Badge> : null}
          </div>
          {isLong ? (
            <ChevronDown
              className={cn(
                "size-4 shrink-0 text-muted-foreground transition-transform",
                expanded && "rotate-180"
              )}
              aria-hidden
            />
          ) : null}
        </div>
        <p className="mt-2 whitespace-pre-wrap">{expanded ? unit.chunk_text : preview}</p>
        {expanded ? <UnitMetadata unit={unit} /> : null}
        {isLong && !expanded ? (
          <p className="mt-1 text-xs text-muted-foreground">Kattints a teljes szövegért</p>
        ) : null}
      </div>
      <SourceAttribution
        sourceId={unit.source_id}
        sourceTitle={unit.source_title}
        sourceUrl={unit.source_url}
        sourceType={unit.source_type}
        channelUrl={unit.channel_url}
      />
    </div>
  );
}

export function MemoryPageStandalone() {
  const { personaId, setPersonaId } = usePersonaPageState();

  return (
    <div className="space-y-4">
      <PageHeader
        title="Memória"
        description="Knowledge unit böngésző és statisztika."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />
      <MemoryPageClient personaId={personaId} />
    </div>
  );
}

export function MemoryPageClient({ personaId }: { personaId: string }) {
  const { personas } = usePersonaOptions();
  const showAllPersonas = personaId === ALL_PERSONAS;
  const personaLabels = Object.fromEntries(
    personas.map((persona) => [persona.persona_id, persona.display_name])
  );
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
    queryFn: () => (showAllPersonas ? fetchAllUnitStats() : fetchUnitStats(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
  });

  const unitsQuery = useQuery({
    queryKey: ["units", personaId, platform, contentType, confidence, duplicatesOnly, unitTextFilter],
    queryFn: () => {
      const params = Object.fromEntries(
        Object.entries({
          limit: "100",
          platform,
          content_type: contentType,
          confidence,
          duplicates_only: duplicatesOnly ? "true" : "",
          q: unitTextFilter.trim(),
        }).filter(([, value]) => Boolean(value))
      );
      return showAllPersonas ? fetchAllUnits(params) : fetchUnits(personaId, params);
    },
    enabled: showAllPersonas || Boolean(personaId),
  });

  const filteredUnits = unitsQuery.data ?? [];

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
      <QueryError error={statsQuery.error ?? unitsQuery.error} />
      <SemanticSearchPanel personaId={personaId} disabled={showAllPersonas} />

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
            <Input
              value={unitTextFilter}
              onChange={(e) => setUnitTextFilter(e.target.value)}
              placeholder="Keresés szövegben, idézetben vagy forráscímben..."
              className="max-w-md"
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
            filteredUnits.map((unit) => (
              <UnitCard
                key={`${unit.persona_id}-${unit.id}`}
                unit={unit}
                personaLabel={
                  showAllPersonas
                    ? (personaLabels[unit.persona_id] ?? unit.persona_id)
                    : undefined
                }
              />
            ))
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
