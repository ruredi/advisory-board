"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { RunStatusBadge } from "@/components/shared/run-status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createJob, fetchAllRuns, fetchJobs, fetchRuns, stopJob } from "@/lib/api/client";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { formatDateTime, formatUsd } from "@/lib/format";

export function LiveActivityRail({
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
  const [showLaunchForm, setShowLaunchForm] = useState(false);
  const [onlyPlatform, setOnlyPlatform] = useState("");
  const [retryFailed, setRetryFailed] = useState(false);
  const [skipDiscovery, setSkipDiscovery] = useState(true);
  const queryClient = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: 3000,
  });
  const runsQuery = useQuery({
    queryKey: ["runs", personaId],
    queryFn: () => (showAllPersonas ? fetchAllRuns() : fetchRuns(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 5000,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setShowLaunchForm(false);
    },
  });

  const stopJobMutation = useMutation({
    mutationFn: (jobId: string) => stopJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const jobs = showAllPersonas
    ? (jobsQuery.data ?? [])
    : (jobsQuery.data ?? []).filter((job) => job.persona_id === personaId);
  const activeJob = jobs.find((job) => job.status === "running") ?? null;
  const recentRuns = (runsQuery.data ?? []).slice(0, 3);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Élő aktivitás</CardTitle>
        <Link href="/runs" className="text-xs text-primary underline underline-offset-2">
          Összes futás →
        </Link>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Aktív job</p>
            {activeJob ? (
              <div className="space-y-2 rounded-md border p-2.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge>running</Badge>
                    {showAllPersonas ? (
                      <span className="text-muted-foreground">
                        {personaLabels[activeJob.persona_id] ?? activeJob.persona_id}
                      </span>
                    ) : null}
                  </div>
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => stopJobMutation.mutate(activeJob.job_id)}
                  >
                    Leállítás
                  </Button>
                </div>
                <p className="truncate text-muted-foreground">
                  {activeJob.log_tail.at(-1) ?? "…"}
                </p>
              </div>
            ) : showAllPersonas ? (
              <p className="text-xs text-muted-foreground">
                Válassz egy advisort a build indításához.
              </p>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Nincs futó job.</p>
                {showLaunchForm ? (
                  <div className="space-y-2 rounded-md border p-2.5 text-xs">
                    <Select
                      value={onlyPlatform || "__all__"}
                      onValueChange={(value) => setOnlyPlatform(value === "__all__" ? "" : value)}
                    >
                      <SelectTrigger className="w-full" size="sm">
                        <SelectValue placeholder="Összes platform" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__all__">Összes platform</SelectItem>
                        <SelectItem value="youtube">YouTube</SelectItem>
                        <SelectItem value="spotify">Spotify</SelectItem>
                        <SelectItem value="x">X</SelectItem>
                        <SelectItem value="instagram">Instagram</SelectItem>
                        <SelectItem value="web">Web</SelectItem>
                      </SelectContent>
                    </Select>
                    <div className="flex items-center gap-1.5">
                      <Checkbox
                        id="live-retry-failed"
                        checked={retryFailed}
                        onCheckedChange={(checked) => setRetryFailed(checked === true)}
                      />
                      <Label htmlFor="live-retry-failed">retry-failed</Label>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Checkbox
                        id="live-skip-discovery"
                        checked={skipDiscovery}
                        onCheckedChange={(checked) => setSkipDiscovery(checked === true)}
                      />
                      <Label htmlFor="live-skip-discovery">skip-discovery</Label>
                    </div>
                    <div className="flex gap-2">
                      <Button size="xs" onClick={() => startJob.mutate()} disabled={startJob.isPending}>
                        Indítás
                      </Button>
                      <Button size="xs" variant="ghost" onClick={() => setShowLaunchForm(false)}>
                        Mégse
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button size="xs" variant="outline" onClick={() => setShowLaunchForm(true)}>
                    Build indítása
                  </Button>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2 sm:col-span-2">
            <p className="text-xs font-medium text-muted-foreground">Legutóbbi futások</p>
            {recentRuns.length === 0 ? (
              <p className="text-xs text-muted-foreground">Még nem futott pipeline.</p>
            ) : (
              <div className="space-y-1.5">
                {recentRuns.map((run) => (
                  <Link
                    key={`${run.persona_id}-${run.run_id}`}
                    href={`/runs/${run.run_id}?persona=${run.persona_id}`}
                    className="flex items-center justify-between gap-2 rounded-md border p-2 text-xs hover:bg-muted/50"
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-muted-foreground">#{run.run_id}</span>
                      <RunStatusBadge status={run.status} />
                      {showAllPersonas ? (
                        <span className="text-muted-foreground">
                          {personaLabels[run.persona_id] ?? run.persona_id}
                        </span>
                      ) : null}
                    </span>
                    <span className="text-muted-foreground">{formatDateTime(run.started_at)}</span>
                    <span className="tabular-nums">{formatUsd(run.cost_usd)}</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
