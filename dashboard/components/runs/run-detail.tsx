"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { MetricCard } from "@/components/shared/metric-card";
import { RunStatusBadge } from "@/components/shared/run-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchRun, fetchRunEvents, stopRun } from "@/lib/api/client";
import { formatDateTime, formatUsd } from "@/lib/format";
import { useElapsedDuration } from "@/lib/hooks/use-elapsed-duration";
import { runStatusLabel } from "@/lib/run-status";

function RunDurationValue({
  startedAt,
  stoppedAt,
  status,
  activeDurationSeconds,
}: {
  startedAt: string;
  stoppedAt: string | null;
  status: string;
  activeDurationSeconds: number;
}) {
  const isRunning = status === "running";
  return (
    <>
      {useElapsedDuration(
        startedAt,
        stoppedAt,
        isRunning,
        isRunning ? undefined : activeDurationSeconds
      )}
    </>
  );
}

export function RunDetailClient({ runId }: { runId: number }) {
  const searchParams = useSearchParams();
  const personaId = searchParams.get("persona") ?? "hormozi";
  const queryClient = useQueryClient();

  const runQuery = useQuery({
    queryKey: ["run", personaId, runId],
    queryFn: () => fetchRun(personaId, runId),
    refetchInterval: 3000,
  });

  const eventsQuery = useQuery({
    queryKey: ["run-events", personaId, runId],
    queryFn: () => fetchRunEvents(personaId, runId, 0),
    refetchInterval: 3000,
    enabled: Boolean(personaId),
  });

  const stopRunMutation = useMutation({
    mutationFn: () => stopRun(personaId, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["run", personaId, runId] });
      queryClient.invalidateQueries({ queryKey: ["runs", personaId] });
      queryClient.invalidateQueries({ queryKey: ["run-events", personaId, runId] });
    },
  });

  const run = runQuery.data;
  const events = eventsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/runs" className="text-sm text-muted-foreground underline">
            ← Futások
          </Link>
          <h1 className="font-heading mt-2 text-2xl font-semibold">Run #{runId}</h1>
        </div>
        {run?.status === "running" ? (
          <Button
            variant="destructive"
            onClick={() => stopRunMutation.mutate()}
            disabled={stopRunMutation.isPending}
          >
            {stopRunMutation.isPending ? "Leállítás…" : "Leállítás"}
          </Button>
        ) : null}
      </div>

      {run ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
          <Card size="sm">
            <CardContent>
              <p className="text-xs text-muted-foreground">Státusz</p>
              <RunStatusBadge status={run.status} />
            </CardContent>
          </Card>
          <MetricCard label="Mód" value={run.run_mode} />
          <MetricCard label="Talált forrás" value={run.sources_discovered} />
          <MetricCard label="Feldolgozva" value={run.sources_processed} />
          <MetricCard label="Költség" value={formatUsd(run.cost_run_usd)} />
          <MetricCard
            label="Skip / Hiba"
            value={`${run.skip_count} / ${run.error_count}`}
          />
          <MetricCard
            label="Nettó futásidő"
            value={
              <RunDurationValue
                startedAt={run.started_at}
                stoppedAt={run.stopped_at}
                status={run.status}
                activeDurationSeconds={run.active_duration_seconds}
              />
            }
          />
          <MetricCard label="Indítva" value={formatDateTime(run.started_at)} />
          <MetricCard
            label="Befejezés"
            value={run.stopped_at ? formatDateTime(run.stopped_at) : "—"}
          />
        </div>
      ) : null}

      {run?.stop_reason && run.status !== "running" ? (
        <p className="text-sm text-muted-foreground">
          Leállás oka: {runStatusLabel(run.status)}
          {run.stop_reason === "fatal_error" ? " — ismétlődő infrastruktúra-hiba miatt automatikusan leállt" : null}
          {run.stop_reason === "interrupted" ? " — manuálisan vagy külső megszakítás miatt" : null}
        </p>
      ) : null}

      {run?.current_title ? (
        <Card>
          <CardHeader><CardTitle>Most feldolgozás alatt</CardTitle></CardHeader>
          <CardContent className="text-sm">
            <p className="font-medium">{run.current_title}</p>
            <p className="text-muted-foreground">{run.current_platform} · {run.current_stage}</p>
            <a href={run.current_url} className="text-primary underline break-all">{run.current_url}</a>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>Eseményfolyam</CardTitle></CardHeader>
        <CardContent className="max-h-[32rem] space-y-2 overflow-y-auto font-mono text-xs">
          {events.map((event) => (
            <div
              key={event.id}
              className={
                event.stage === "source_error" || event.stage === "run_aborted"
                  ? "text-destructive"
                  : ""
              }
            >
              <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>{" "}
              <span className="font-semibold">{event.stage}</span> {event.message}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
