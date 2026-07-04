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
  return stage.replaceAll("_", " ");
}

function DiscoveryEventLine({ event }: { event: PipelineEvent }) {
  const isError =
    event.message.toLowerCase().includes("hiba") || event.message.toLowerCase().includes("error");
  return (
    <div className={cn("font-mono text-[11px]", isError && "text-destructive")}>
      <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>{" "}
      <span className="font-medium text-foreground/80">{stageLabel(event.stage)}</span>{" "}
      {event.message}
    </div>
  );
}

export function SourceDiscoveryProgress({
  personaId,
  trackedJob,
  relevantRun,
  recentEvents,
  isRunning,
  isFinished,
  onStop,
  stopPending,
}: {
  personaId: string;
  trackedJob: JobItem;
  relevantRun: SyncRunDetail | null;
  runDetail?: RunProgress | undefined;
  recentEvents: PipelineEvent[];
  isRunning: boolean;
  isFinished: boolean;
  onStop: () => void;
  stopPending: boolean;
}) {
  const discoveryEvents = useMemo(
    () => recentEvents.filter((event) => event.stage === "discovery"),
    [recentEvents]
  );

  const logLines = useMemo(
    () => trackedJob.log_tail.filter((line) => line.includes("discovery:")).slice(-30),
    [trackedJob.log_tail]
  );

  const latestEvent = discoveryEvents.at(-1);
  const latestLog = logLines.at(-1)?.replace(/^discovery:\s*/, "");
  const discoveredCount = relevantRun?.sources_discovered ?? 0;

  const timeline = useMemo(() => {
    const items: Array<{ key: string; kind: "event" | "log"; text: string; time?: string }> = [];
    for (const event of discoveryEvents) {
      items.push({
        key: `event-${event.id}`,
        kind: "event",
        text: event.message,
        time: event.created_at,
      });
    }
    if (items.length === 0) {
      for (const [index, line] of logLines.entries()) {
        items.push({ key: `log-${index}`, kind: "log", text: line.replace(/^discovery:\s*/, "") });
      }
    }
    return items;
  }, [discoveryEvents, logLines]);

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
  }, [discoveryEvents, logLines, isRunning]);

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
            {relevantRun ? (
              <Link
                href={`/runs/${relevantRun.run_id}?persona=${personaId}`}
                className="text-primary underline underline-offset-2"
              >
                Run #{relevantRun.run_id}
              </Link>
            ) : null}
            {discoveredCount > 0 ? (
              <span className="text-muted-foreground tabular-nums">
                {discoveredCount} új forrás
              </span>
            ) : isRunning ? (
              <span className="text-muted-foreground">új források keresése…</span>
            ) : null}
          </div>

          <p className="truncate text-xs text-muted-foreground">
            {latestEvent
              ? latestEvent.message
              : latestLog ?? (isRunning ? "Keresés folyamatban…" : "Várakozás a kimenetre…")}
          </p>

          {isFinished ? (
            <p className="text-xs">
              {trackedJob.status === "succeeded"
                ? discoveredCount > 0
                  ? `Keresés kész — ${discoveredCount} új forrás (pending).`
                  : "Keresés kész — nincs új forrás."
                : `Keresés megszakadt (exit ${trackedJob.exit_code ?? "—"}).`}
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
          {discoveryEvents.length > 0
            ? discoveryEvents.map((event) => <DiscoveryEventLine key={event.id} event={event} />)
            : logLines.map((line, index) => (
                <div key={index} className="font-mono text-[11px] text-muted-foreground">
                  {line.replace(/^discovery:\s*/, "")}
                </div>
              ))}
        </div>
      ) : null}
    </div>
  );
}
