"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createJob, fetchJobs, fetchRuns, stopJob } from "@/lib/api/client";
import { formatDateTime, formatUsd } from "@/lib/format";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

export function RunsPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [onlyPlatform, setOnlyPlatform] = useState("");
  const [retryFailed, setRetryFailed] = useState(false);
  const [skipDiscovery, setSkipDiscovery] = useState(true);
  const queryClient = useQueryClient();

  const runsQuery = useQuery({
    queryKey: ["runs", personaId],
    queryFn: () => fetchRuns(personaId),
    enabled: Boolean(personaId),
    refetchInterval: 5000,
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: 3000,
  });

  const startJob = useMutation({
    mutationFn: () =>
      createJob({
        persona_id: personaId,
        kind: "build",
        only_platform: onlyPlatform || null,
        retry_failed: retryFailed,
        skip_discovery: skipDiscovery,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const stopJobMutation = useMutation({
    mutationFn: (jobId: string) => stopJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Futások"
        description="Sync run history és pipeline indítás."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={runsQuery.error} />

      <Card>
        <CardHeader>
          <CardTitle>Pipeline indítás</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">Platform</span>
            <select
              value={onlyPlatform}
              onChange={(e) => setOnlyPlatform(e.target.value)}
              className="rounded-md border bg-background px-3 py-2"
            >
              <option value="">Összes</option>
              <option value="youtube">YouTube</option>
              <option value="spotify">Spotify</option>
              <option value="x">X</option>
              <option value="instagram">Instagram</option>
              <option value="web">Web</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={retryFailed} onChange={(e) => setRetryFailed(e.target.checked)} />
            retry-failed
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={skipDiscovery} onChange={(e) => setSkipDiscovery(e.target.checked)} />
            skip-discovery
          </label>
          <Button onClick={() => startJob.mutate()} disabled={startJob.isPending}>
            Build indítása
          </Button>
        </CardContent>
      </Card>

      {(jobsQuery.data ?? []).length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Aktív jobok</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(jobsQuery.data ?? []).map((job) => (
              <div key={job.job_id} className="rounded-md border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={job.status === "running" ? "default" : "secondary"}>{job.status}</Badge>
                    <span className="font-mono text-xs">{job.job_id}</span>
                  </div>
                  {job.status === "running" ? (
                    <Button size="sm" variant="outline" onClick={() => stopJobMutation.mutate(job.job_id)}>
                      Leállítás
                    </Button>
                  ) : null}
                </div>
                <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-xs text-muted-foreground">
                  {job.log_tail.slice(-8).join("\n")}
                </pre>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Run history</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4">Run</th>
                <th className="py-2 pr-4">Státusz</th>
                <th className="py-2 pr-4">Indítva</th>
                <th className="py-2 pr-4" title="Sikeresen indexelt források (source_done)">Kész</th>
                <th className="py-2 pr-4" title="Kihagyott források">Skip</th>
                <th className="py-2 pr-4" title="Knowledge unitok (run végén)">Unitok</th>
                <th className="py-2 pr-4">Hibák</th>
                <th className="py-2 pr-4">Költség</th>
                <th className="py-2 pr-4">API hívás</th>
              </tr>
            </thead>
            <tbody>
              {(runsQuery.data ?? []).map((run) => (
                <tr key={run.run_id} className="border-b">
                  <td className="py-2 pr-4">
                    <Link href={`/runs/${run.run_id}?persona=${personaId}`} className="text-primary underline">
                      #{run.run_id}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={run.status === "running" ? "default" : "secondary"}>{run.status}</Badge>
                  </td>
                  <td className="py-2 pr-4">{formatDateTime(run.started_at)}</td>
                  <td className="py-2 pr-4 tabular-nums">{run.done_count}</td>
                  <td className="py-2 pr-4 tabular-nums">{run.skip_count}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {run.units_created > 0 ? run.units_created : run.status === "running" ? "—" : run.units_created}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{run.errors}</td>
                  <td className="py-2 pr-4 tabular-nums">{formatUsd(run.cost_usd)}</td>
                  <td className="py-2 pr-4 tabular-nums">{run.api_calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
