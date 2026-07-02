"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchRun, fetchRunEvents } from "@/lib/api/client";
import { formatDateTime, formatUsd } from "@/lib/format";
import { useElapsedDuration } from "@/lib/hooks/use-elapsed-duration";

function RunDuration({
  startedAt,
  finishedAt,
  status,
}: {
  startedAt: string;
  finishedAt: string | null;
  status: string;
}) {
  const isRunning = status === "running" && finishedAt === null;
  const duration = useElapsedDuration(startedAt, finishedAt, isRunning);

  return (
    <Card size="sm">
      <CardContent>
        <p className="text-xs text-muted-foreground">Futásidő</p>
        <p className="font-semibold tabular-nums">{duration}</p>
      </CardContent>
    </Card>
  );
}

export function RunDetailClient({ runId }: { runId: number }) {
  const searchParams = useSearchParams();
  const personaId = searchParams.get("persona") ?? "hormozi";

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

  const run = runQuery.data;
  const events = eventsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <Link href="/runs" className="text-sm text-muted-foreground underline">
          ← Futások
        </Link>
        <h1 className="font-heading mt-2 text-2xl font-semibold">Run #{runId}</h1>
      </div>

      {run ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Card size="sm"><CardContent><p className="text-xs text-muted-foreground">Státusz</p><Badge>{run.status}</Badge></CardContent></Card>
          <Card size="sm"><CardContent><p className="text-xs text-muted-foreground">Költség</p><p className="font-semibold tabular-nums">{formatUsd(run.cost_run_usd)}</p></CardContent></Card>
          <Card size="sm"><CardContent><p className="text-xs text-muted-foreground">Done / Error / Skip</p><p>{run.done_count} / {run.error_count} / {run.skip_count}</p></CardContent></Card>
          <RunDuration startedAt={run.started_at} finishedAt={run.finished_at} status={run.status} />
          <Card size="sm"><CardContent><p className="text-xs text-muted-foreground">Indítva</p><p>{formatDateTime(run.started_at)}</p></CardContent></Card>
        </div>
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
            <div key={event.id} className={event.stage === "source_error" ? "text-destructive" : ""}>
              <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>{" "}
              <span className="font-semibold">{event.stage}</span> {event.message}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
