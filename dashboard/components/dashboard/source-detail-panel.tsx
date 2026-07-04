"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink } from "@/lib/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { SourceIdentity } from "@/components/shared/source-identity";
import { SourceStatusChip } from "@/components/shared/source-status-chip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchQuotes,
  fetchSource,
  fetchSourceSegments,
  fetchSourceTranscript,
  fetchUnits,
  patchSource,
} from "@/lib/api/client";
import type { SourceWithMemoryItem, TranscriptSegmentItem } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type DetailTab = "overview" | "full" | "persona" | "extraction" | "units" | "segments";

const TAB_LABELS: Record<DetailTab, string> = {
  overview: "Áttekintés",
  full: "Teljes transcript",
  persona: "Persona transcript",
  extraction: "Extraction input",
  units: "Knowledge unitok",
  segments: "Segmentek",
};

const TRANSCRIPT_STATUS_LABELS: Record<string, string> = {
  labeled: "Címkézett",
  unlabeled: "Címkézetlen",
  fallback: "Fallback VTT",
  failed_diarization: "Diarization hiba",
};

function TabButton({
  tab,
  active,
  onClick,
}: {
  tab: DetailTab;
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
      {TAB_LABELS[tab]}
    </Button>
  );
}

function TranscriptViewer({
  personaId,
  sourceId,
  variant,
}: {
  personaId: string;
  sourceId: number;
  variant: "document" | "persona" | "extraction_input";
}) {
  const transcriptQuery = useQuery({
    queryKey: ["source-transcript", personaId, sourceId, variant],
    queryFn: () => fetchSourceTranscript(personaId, sourceId, variant),
    enabled: Boolean(personaId && sourceId),
  });

  if (transcriptQuery.isLoading) {
    return <Skeleton className="h-48 rounded" />;
  }
  if (transcriptQuery.error) {
    return <p className="text-xs text-muted-foreground">Transcript nem elérhető.</p>;
  }
  if (!transcriptQuery.data) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {transcriptQuery.data.label} · {transcriptQuery.data.char_count.toLocaleString("hu-HU")} karakter
      </p>
      <pre className="max-h-96 overflow-auto rounded-md border bg-muted/30 p-2.5 text-xs whitespace-pre-wrap">
        {transcriptQuery.data.text}
      </pre>
    </div>
  );
}

function SegmentViewer({
  personaId,
  sourceId,
}: {
  personaId: string;
  sourceId: number;
}) {
  const [speakerFilter, setSpeakerFilter] = useState("");
  const [search, setSearch] = useState("");
  const segmentsQuery = useQuery({
    queryKey: ["source-segments", personaId, sourceId],
    queryFn: () => fetchSourceSegments(personaId, sourceId),
    enabled: Boolean(personaId && sourceId),
  });

  const filteredSegments = useMemo(() => {
    const segments = segmentsQuery.data?.segments ?? [];
    const needle = search.trim().toLowerCase();
    return segments.filter((segment) => {
      if (speakerFilter && segment.speaker_type !== speakerFilter) return false;
      if (needle && !segment.text.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [segmentsQuery.data?.segments, search, speakerFilter]);

  if (segmentsQuery.isLoading) return <Skeleton className="h-48 rounded" />;
  if (segmentsQuery.error) {
    return <p className="text-xs text-muted-foreground">Nincs strukturált segment JSON ehhez a forráshoz.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {(["", "target", "other", "unknown"] as const).map((value) => (
          <Button
            key={value || "all"}
            type="button"
            size="xs"
            variant={speakerFilter === value ? "default" : "outline"}
            onClick={() => setSpeakerFilter(value)}
          >
            {value || "mind"}
          </Button>
        ))}
      </div>
      <Input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Keresés a segmentekben..."
        className="max-w-md"
      />
      <div className="max-h-96 space-y-2 overflow-auto">
        {filteredSegments.map((segment: TranscriptSegmentItem) => (
          <div
            key={segment.segment_id}
            className={cn(
              "rounded-md border p-2 text-xs",
              segment.speaker_type === "target" && "border-primary/30 bg-primary/5"
            )}
          >
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant="secondary">{segment.speaker}</Badge>
              <Badge variant="outline">{segment.speaker_type}</Badge>
              {segment.start_seconds != null ? (
                <Badge variant="outline">{Math.floor(segment.start_seconds)}s</Badge>
              ) : null}
            </div>
            <p className="mt-1.5 whitespace-pre-wrap text-muted-foreground">{segment.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SourceDetailPanel({
  personaId,
  sourceId,
  personaLabel,
  summary,
  variant = "card",
}: {
  personaId: string;
  sourceId: number | null;
  personaLabel?: string;
  summary: SourceWithMemoryItem | null;
  variant?: "card" | "plain";
}) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<DetailTab>("overview");

  useEffect(() => {
    setTab("overview");
  }, [sourceId, personaId]);

  const detailQuery = useQuery({
    queryKey: ["source", personaId, sourceId],
    queryFn: () => fetchSource(personaId, sourceId!),
    enabled: sourceId !== null,
  });

  const unitsQuery = useQuery({
    queryKey: ["units-by-source", personaId, sourceId],
    queryFn: () => fetchUnits(personaId, { source_id: String(sourceId), limit: "50" }),
    enabled: sourceId !== null && tab === "units",
  });

  const quotesQuery = useQuery({
    queryKey: ["quotes-by-source", personaId, sourceId],
    queryFn: () => fetchQuotes(personaId, { source_id: String(sourceId), limit: "20" }),
    enabled: sourceId !== null && tab === "units",
  });

  const patchMutation = useMutation({
    mutationFn: ({ nextStatus }: { nextStatus: string }) =>
      patchSource(personaId, sourceId!, nextStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources-with-memory", personaId] });
      queryClient.invalidateQueries({ queryKey: ["sources", personaId] });
      queryClient.invalidateQueries({ queryKey: ["source-stats", personaId] });
      queryClient.invalidateQueries({ queryKey: ["source", personaId, sourceId] });
    },
  });

  if (sourceId === null) {
    if (variant === "plain") {
      return null;
    }
    return (
      <Card>
        <CardHeader>
          <CardTitle>Részletek</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Válassz forrást a listából.</p>
        </CardContent>
      </Card>
    );
  }

  const detail = detailQuery.data;
  const hasSegments = detail?.transcript_variants.some((variant) => variant.key === "labeled" && variant.available);

  const header = (
    <div className="space-y-3">
      {variant === "card" ? <CardTitle>Részletek</CardTitle> : null}
      <div className="flex flex-wrap gap-1.5">
        {(Object.keys(TAB_LABELS) as DetailTab[]).map((value) =>
          value === "segments" && !hasSegments ? null : (
            <TabButton key={value} tab={value} active={tab === value} onClick={() => setTab(value)} />
          )
        )}
      </div>
    </div>
  );

  const body = (
    <div className="space-y-4 text-sm">
        {detailQuery.isLoading || !detail ? (
          <div className="space-y-2">
            <Skeleton className="h-5 w-3/4 rounded" />
            <Skeleton className="h-4 w-1/2 rounded" />
            <Skeleton className="h-24 rounded" />
          </div>
        ) : tab === "overview" ? (
          <>
            <SourceIdentity
              title={detail.source_title}
              sourceUrl={detail.source_url}
              sourceType={detail.source_type}
              channelUrl={detail.channel_url}
              size="md"
              subtitle={
                <span className="flex flex-wrap items-center gap-2">
                  {detail.platform}
                  <SourceStatusChip status={detail.status} />
                  <Badge variant="outline">
                    {TRANSCRIPT_STATUS_LABELS[detail.transcript_status] ?? detail.transcript_status}
                  </Badge>
                </span>
              }
            />

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

            {summary?.latest_event_stage ? (
              <div className="rounded-md border bg-muted/30 p-2.5 text-xs text-muted-foreground">
                <span className="font-medium text-foreground/80">{summary.latest_event_stage}</span>{" "}
                {summary.latest_event_message}
                {summary.latest_event_at ? <span> · {formatDateTime(summary.latest_event_at)}</span> : null}
              </div>
            ) : null}

            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              {personaLabel ? (
                <>
                  <dt className="text-muted-foreground">Advisor</dt>
                  <dd className="text-right font-medium">{personaLabel}</dd>
                </>
              ) : null}
              <dt className="text-muted-foreground">Knowledge unitok</dt>
              <dd className="text-right font-medium tabular-nums">{detail.unit_count}</dd>
              <dt className="text-muted-foreground">Transcript státusz</dt>
              <dd className="text-right">
                {TRANSCRIPT_STATUS_LABELS[detail.transcript_status] ?? detail.transcript_status}
              </dd>
              {detail.source_date ? (
                <>
                  <dt className="text-muted-foreground">Publikálva</dt>
                  <dd className="text-right tabular-nums">{detail.source_date}</dd>
                </>
              ) : null}
              {detail.processed_at ? (
                <>
                  <dt className="text-muted-foreground">Feldolgozva</dt>
                  <dd className="text-right tabular-nums">{formatDateTime(detail.processed_at)}</dd>
                </>
              ) : null}
            </dl>

            <div className="flex flex-wrap gap-2">
              {detail.status !== "pending" ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={patchMutation.isPending}
                  onClick={() => patchMutation.mutate({ nextStatus: "pending" })}
                >
                  Újra sorba állít
                </Button>
              ) : null}
              {detail.status !== "skipped" ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={patchMutation.isPending}
                  onClick={() => patchMutation.mutate({ nextStatus: "skipped" })}
                >
                  Kihagy
                </Button>
              ) : null}
            </div>
          </>
        ) : tab === "full" ? (
          <TranscriptViewer personaId={personaId} sourceId={sourceId} variant="document" />
        ) : tab === "persona" ? (
          <TranscriptViewer personaId={personaId} sourceId={sourceId} variant="persona" />
        ) : tab === "extraction" ? (
          <TranscriptViewer personaId={personaId} sourceId={sourceId} variant="extraction_input" />
        ) : tab === "segments" ? (
          <SegmentViewer personaId={personaId} sourceId={sourceId} />
        ) : (
          <div className="space-y-4">
            {(unitsQuery.data ?? []).length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Memória ebből a forrásból ({unitsQuery.data!.length})
                </p>
                <div className="max-h-64 space-y-2 overflow-auto">
                  {unitsQuery.data!.map((unit) => (
                    <div key={unit.id} className="rounded-md border p-2 text-xs">
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant="secondary">{unit.content_type}</Badge>
                        <Badge>{unit.confidence}</Badge>
                        {unit.duplicate_of ? <Badge variant="outline">dup #{unit.duplicate_of}</Badge> : null}
                      </div>
                      <p className="mt-1.5 text-muted-foreground">
                        {unit.chunk_text.slice(0, 180)}
                        {unit.chunk_text.length > 180 ? "…" : ""}
                      </p>
                      {unit.quotes?.length ? (
                        <div className="mt-2 space-y-1">
                          {unit.quotes.map((quote, index) => (
                            <blockquote key={index} className="rounded border bg-muted/20 p-1.5 italic">
                              “{String(quote.text ?? "")}”
                            </blockquote>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Ehhez a forráshoz még nincs indexelt unit.</p>
            )}

            {(quotesQuery.data ?? []).length > 0 ? (
              <div className="space-y-2 border-t pt-3">
                <p className="text-xs font-medium text-muted-foreground">Idézetek ({quotesQuery.data!.length})</p>
                <div className="space-y-2">
                  {quotesQuery.data!.map((quote, index) => (
                    <div key={`${quote.unit_id}-${index}`} className="rounded-md border p-2 text-xs">
                      <blockquote className="italic">“{quote.text}”</blockquote>
                      <div className="mt-1 flex flex-wrap gap-1.5">
                        {quote.speaker ? <Badge variant="secondary">{quote.speaker}</Badge> : null}
                        {quote.start_seconds != null ? (
                          <Badge variant="outline">{Math.floor(quote.start_seconds)}s</Badge>
                        ) : null}
                      </div>
                      {quote.source_link ? (
                        <a
                          href={quote.source_link}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
                        >
                          <ExternalLink className="size-3.5" />
                          Forrás link
                        </a>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
    </div>
  );

  if (variant === "plain") {
    return (
      <div key={sourceId} className="space-y-4">
        {header}
        {body}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>{header}</CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
