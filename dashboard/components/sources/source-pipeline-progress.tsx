"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";

import { RunStatusBadge } from "@/components/shared/run-status-badge";
import { Button } from "@/components/ui/button";
import type { JobItem, PipelineEvent, RunProgress, SyncRunDetail } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

function stageLabel(stage: string): string {
  if (stage === "discovery") return "Keresés";
  if (stage === "source_start") return "Indítás";
  if (stage === "source_done") return "Kész";
  if (stage === "source_error") return "Hiba";
  if (stage === "source_fetch") return "Letöltés";
  if (stage === "source_extract") return "Kivonás";
  if (stage === "source_index") return "Indexelés";
  return stage.replaceAll("_", " ");
}

function PipelineEventLine({ event }: { event: PipelineEvent }) {
  const isError =
    event.stage === "source_error" ||
    event.message.toLowerCase().includes("hiba") ||
    event.message.toLowerCase().includes("error");
  return (
    <div className={cn("font-mono text-[11px]", isError && "text-destructive")}>
      <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>{" "}
      <span className="font-medium text-foreground/80">{stageLabel(event.stage)}</span>{" "}
      {event.message}
    </div>
  );
}

export function SourcePipelineProgress({
  personaId,
  mode,
  trackedJob,
  relevantRun,
  recentEvents,
  isRunning,
  isFinished,
  onStop,
  stopPending,
}: {
  personaId: string;
  mode: "discovery" | "process";
  trackedJob: JobItem;
  relevantRun: SyncRunDetail | null;
  runDetail?: RunProgress | undefined;
  recentEvents: PipelineEvent[];
  isRunning: boolean;
  isFinished: boolean;
  onStop: () => void;
  stopPending: boolean;
}) {
  const isDiscovery = mode === "discovery";

  const filteredEvents = useMemo(() => {
    if (isDiscovery) {
      return recentEvents.filter((event) => event.stage === "discovery");
    }
    return recentEvents.filter((event) =>
      ["source_start", "source_fetch", "source_extract", "source_index", "source_done", "source_error", "source_skip"].includes(
        event.stage
      )
    );
  }, [isDiscovery, recentEvents]);

  const logLines = useMemo(() => {
    if (isDiscovery) {
      return trackedJob.log_tail.filter((line) => line.includes("discovery:")).slice(-30);
    }
    return trackedJob.log_tail
      .filter((line) => /^\[\d+\/\d+\]|pending_sources=|start youtube:|start podcast:|done:|error:/.test(line))
      .slice(-30);
  }, [isDiscovery, trackedJob.log_tail]);

  const latestEvent = filteredEvents.at(-1);
  const latestLog = isDiscovery
    ? logLines.at(-1)?.replace(/^discovery:\s*/, "")
    : logLines.at(-1);
  const discoveredCount = relevantRun?.sources_discovered ?? 0;
  const processedCount = relevantRun?.sources_processed ?? 0;

  const timeline = useMemo(() => {
    const items: Array<{ key: string; kind: "event" | "log"; text: string; time?: string }> = [];
    for (const event of filteredEvents) {
      items.push({
        key: `event-${event.id}`,
        kind: "event",
        text: event.message,
        time: event.created_at,
      });
    }
    if (items.length === 0) {
      for (const [index, line] of logLines.entries()) {
        items.push({
          key: `log-${index}`,
          kind: "log",
          text: isDiscovery ? line.replace(/^discovery:\s*/, "") : line,
        });
      }
    }
    return items;
  }, [filteredEvents, isDiscovery, logLines]);

  const logScrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    if (isRunning) {
      stickToBottomRef.current = true;
    }
  }, [isRunning, trackedJob.job_id]);

  useEffect(() => {
    const element = logScrollRef.current;
    if (!element || !stickToBottomRef.current) {
      return;
    }
    element.scrollTop = element.scrollHeight;
  }, [filteredEvents, logLines, isRunning]);

  const handleLogScroll = () => {
    const element = logScrollRef.current;
    if (!element) {
      return;
    }
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 24;
  };

  return (
    <div
      className={cn(
        "border-b px-(--card-spacing) py-3",
        isFinished && trackedJob.status === "succeeded" && "bg-emerald-500/5",
        isFinished && trackedJob.status !== "succeeded" && "bg-destructive/5"
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <RunStatusBadge status={trackedJob.status} />
            <span className="text-xs font-medium text-muted-foreground">
              {isDiscovery ? "Forrás keresés" : "Feldolgozás"}
            </span>
            {relevantRun ? (
              <Link
                href={`/runs/${relevantRun.run_id}?persona=${personaId}`}
                className="text-primary underline underline-offset-2"
              >
                Run #{relevantRun.run_id}
              </Link>
            ) : null}
            {isDiscovery ? (
              discoveredCount > 0 ? (
                <span className="text-muted-foreground tabular-nums">{discoveredCount} új forrás</span>
              ) : isRunning ? (
                <span className="text-muted-foreground">keresés folyamatban…</span>
              ) : null
            ) : processedCount > 0 || isRunning ? (
              <span className="text-muted-foreground tabular-nums">
                {processedCount > 0 ? `${processedCount} feldolgozva` : "feldolgozás folyamatban…"}
              </span>
            ) : null}
          </div>

          <p className="truncate text-xs text-muted-foreground">
            {latestEvent
              ? latestEvent.message
              : latestLog ?? (isRunning ? (isDiscovery ? "Keresés folyamatban…" : "Feldolgozás folyamatban…") : "Várakozás a kimenetre…")}
          </p>

          {isFinished ? (
            <p className="text-xs">
              {trackedJob.status === "succeeded"
                ? isDiscovery
                  ? discoveredCount > 0
                    ? `Keresés kész — ${discoveredCount} új forrás (pending).`
                    : "Keresés kész — nincs új forrás."
                  : processedCount > 0
                    ? `Feldolgozás kész — ${processedCount} forrás feldolgozva.`
                    : "Feldolgozás kész — nem volt feldolgozandó pending forrás."
                : `${isDiscovery ? "Keresés" : "Feldolgozás"} megszakadt (exit ${trackedJob.exit_code ?? "—"}).`}
            </p>
          ) : null}
        </div>

        {isRunning ? (
          <Button size="sm" variant="outline" onClick={onStop} disabled={stopPending}>
            Leállítás
          </Button>
        ) : null}
      </div>

      {timeline.length > 0 ? (
        <div
          ref={logScrollRef}
          onScroll={handleLogScroll}
          className="mt-2 max-h-56 space-y-0.5 overflow-y-auto rounded-md border bg-muted/20 p-2.5"
        >
          {filteredEvents.length > 0
            ? filteredEvents.map((event) => <PipelineEventLine key={event.id} event={event} />)
            : logLines.map((line, index) => (
                <div key={index} className="font-mono text-[11px] text-muted-foreground">
                  {isDiscovery ? line.replace(/^discovery:\s*/, "") : line}
                </div>
              ))}
        </div>
      ) : null}
    </div>
  );
}
