"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { QueryError } from "@/components/shared/api-guard";
import { PageHeader } from "@/components/shared/page-header";
import { PersonaSelect } from "@/components/shared/persona-select";
import { RunStatusBadge } from "@/components/shared/run-status-badge";
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
import { ALL_PERSONAS, createJob, fetchAllRuns, fetchJobs, fetchRuns, stopRun } from "@/lib/api/client";
import type { JobItem, SyncRunDetail } from "@/lib/api/types";
import { formatDateTime, formatDurationSeconds, formatUsd } from "@/lib/format";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { RUN_STATUS_FILTERS, runStatusLabel, runStatusVariant } from "@/lib/run-status";
import { cn } from "@/lib/utils";

function RunStatusFilterChip({
  status,
  count,
  active,
  onClick,
}: {
  status: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  const variant = runStatusVariant(status);
  return (
    <Button
      type="button"
      variant="outline"
      size="xs"
      onClick={onClick}
      className={cn(
        "h-auto rounded-full px-2.5 py-1 text-xs font-medium",
        variant === "destructive" && "border-destructive/30 bg-destructive/10 text-destructive",
        variant === "default" && "border-primary/30 bg-primary/10 text-primary",
        variant === "secondary" && "border-border bg-muted/50 text-muted-foreground",
        active
          ? "ring-2 ring-primary/40 ring-offset-1 ring-offset-background"
          : "opacity-80 hover:opacity-100"
      )}
    >
      {runStatusLabel(status)}
      <span className="tabular-nums text-[10px] opacity-70">{count}</span>
    </Button>
  );
}

function RunTableRow({
  run,
  personaLabel,
  showPersona,
  activeJob,
  onStop,
  stopPending,
}: {
  run: SyncRunDetail;
  personaLabel: string;
  showPersona: boolean;
  activeJob: JobItem | null;
  onStop: (runId: number, personaId: string) => void;
  stopPending: boolean;
}) {
  const [expanded, setExpanded] = useState(run.status === "running");
  const isRunning = run.status === "running";
  const showLog = isRunning && activeJob && activeJob.log_tail.length > 0;

  return (
    <>
      <tr className={cn("border-b", isRunning && "bg-primary/5")}>
        <td className="py-2 pr-4">
          <Link
            href={`/runs/${run.run_id}?persona=${run.persona_id}`}
            className="text-primary underline"
          >
            #{run.run_id}
          </Link>
        </td>
        {showPersona ? <td className="py-2 pr-4">{personaLabel}</td> : null}
        <td className="py-2 pr-4">
          <RunStatusBadge status={run.status} />
        </td>
        <td className="py-2 pr-4">{formatDateTime(run.started_at)}</td>
        <td className="py-2 pr-4 tabular-nums">{formatDurationSeconds(run.active_duration_seconds)}</td>
        <td className="py-2 pr-4 text-xs">{run.run_mode}</td>
        <td className="py-2 pr-4 tabular-nums">{run.sources_discovered}</td>
        <td className="py-2 pr-4 tabular-nums">{run.sources_processed}</td>
        <td className="py-2 pr-4 tabular-nums">{run.skip_count}</td>
        <td className="py-2 pr-4 tabular-nums">
          {run.units_created > 0 ? run.units_created : isRunning ? "—" : run.units_created}
        </td>
        <td className="py-2 pr-4 tabular-nums">{run.errors}</td>
        <td className="py-2 pr-4 tabular-nums">{formatUsd(run.cost_usd)}</td>
        <td className="py-2 pr-4 tabular-nums">{run.api_calls}</td>
        <td className="py-2">
          {isRunning ? (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onStop(run.run_id, run.persona_id)}
                disabled={stopPending}
              >
                Leállítás
              </Button>
              {showLog ? (
                <Button size="sm" variant="ghost" onClick={() => setExpanded((value) => !value)}>
                  {expanded ? "Log elrejtése" : "Log"}
                </Button>
              ) : null}
            </div>
          ) : null}
        </td>
      </tr>
      {expanded && showLog ? (
        <tr className="border-b bg-muted/30">
          <td colSpan={showPersona ? 13 : 12} className="px-4 py-2">
            <pre className="max-h-32 overflow-auto whitespace-pre-wrap font-mono text-xs text-muted-foreground">
              {activeJob.log_tail.slice(-12).join("\n")}
            </pre>
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function RunsPageStandalone() {
  const [filterPersonaId, setFilterPersonaId] = useState(ALL_PERSONAS);
  const { defaultPersonaId } = usePersonaOptions();
  const [buildPersonaId, setBuildPersonaId] = useState("");
  const resolvedBuildPersonaId = buildPersonaId || defaultPersonaId;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Futások"
        description="Sync run history és pipeline indítás."
        personaId={filterPersonaId}
        onPersonaChange={setFilterPersonaId}
      />
      <RunsPageClient
        filterPersonaId={filterPersonaId}
        buildPersonaId={resolvedBuildPersonaId}
        onBuildPersonaChange={setBuildPersonaId}
      />
    </div>
  );
}

export function RunsPageClient({
  filterPersonaId,
  buildPersonaId,
  onBuildPersonaChange,
}: {
  filterPersonaId: string;
  buildPersonaId: string;
  onBuildPersonaChange: (personaId: string) => void;
}) {
  const [onlyPlatform, setOnlyPlatform] = useState("");
  const [retryFailed, setRetryFailed] = useState(false);
  const [skipDiscovery, setSkipDiscovery] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const queryClient = useQueryClient();
  const { personas } = usePersonaOptions();
  const showAllPersonas = filterPersonaId === ALL_PERSONAS;

  const personaLabels = useMemo(
    () => Object.fromEntries(personas.map((persona) => [persona.persona_id, persona.display_name])),
    [personas]
  );

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data ?? [];
      const relevantJobs = showAllPersonas
        ? jobs
        : jobs.filter((job) => job.persona_id === filterPersonaId);
      return relevantJobs.some((job) => job.status === "running") ? 2000 : false;
    },
  });

  const runsQuery = useQuery({
    queryKey: ["runs", filterPersonaId],
    queryFn: () => (showAllPersonas ? fetchAllRuns() : fetchRuns(filterPersonaId)),
    enabled: showAllPersonas || Boolean(filterPersonaId),
    refetchInterval: (query) => {
      const runs = query.state.data ?? [];
      return runs.some((run) => run.status === "running") ? 2000 : 5000;
    },
  });

  const activeJob =
    (jobsQuery.data ?? []).find(
      (job) => job.persona_id === buildPersonaId && job.status === "running"
    ) ?? null;

  const activeJobsByPersona = useMemo(() => {
    const jobs = new Map<string, JobItem>();
    for (const job of jobsQuery.data ?? []) {
      if (job.status === "running") {
        jobs.set(job.persona_id, job);
      }
    }
    return jobs;
  }, [jobsQuery.data]);

  const runs = runsQuery.data ?? [];

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { running: 0, finished: 0, aborted: 0, interrupted: 0 };
    for (const run of runs) {
      if (run.status in counts) counts[run.status] += 1;
    }
    return counts;
  }, [runs]);

  const filteredRuns = useMemo(
    () => (statusFilter ? runs.filter((run) => run.status === statusFilter) : runs),
    [runs, statusFilter]
  );

  const invalidateRunQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["runs"] });
  };

  const startJob = useMutation({
    mutationFn: () =>
      createJob({
        persona_id: buildPersonaId,
        kind: "build",
        only_platform: onlyPlatform || null,
        retry_failed: retryFailed,
        skip_discovery: skipDiscovery,
      }),
    onSuccess: invalidateRunQueries,
  });

  const stopRunMutation = useMutation({
    mutationFn: ({ personaId, runId }: { personaId: string; runId: number }) =>
      stopRun(personaId, runId),
    onSuccess: invalidateRunQueries,
  });

  const toggleStatusFilter = (status: string) => {
    setStatusFilter((current) => (current === status ? "" : status));
  };

  return (
    <div className="space-y-6">
      <QueryError error={runsQuery.error} />

      <Card>
        <CardHeader>
          <CardTitle>Pipeline indítás</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <PersonaSelect value={buildPersonaId} onChange={onBuildPersonaChange} />
          <div className="flex flex-col gap-1 text-sm">
            <Label className="text-muted-foreground">Platform</Label>
            <Select
              value={onlyPlatform || "__all__"}
              onValueChange={(value) => setOnlyPlatform(value === "__all__" ? "" : value)}
            >
              <SelectTrigger className="min-w-40">
                <SelectValue placeholder="Összes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">Összes</SelectItem>
                <SelectItem value="youtube">YouTube</SelectItem>
                <SelectItem value="spotify">Spotify</SelectItem>
                <SelectItem value="x">X</SelectItem>
                <SelectItem value="instagram">Instagram</SelectItem>
                <SelectItem value="web">Web</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Checkbox
              id="retry-failed"
              checked={retryFailed}
              onCheckedChange={(checked) => setRetryFailed(checked === true)}
            />
            <Label htmlFor="retry-failed">Sikertelen újra</Label>
          </div>
          <div
            className="flex items-center gap-2 text-sm"
            title="Ha be van pipálva, nem keres új forrásokat — csak a meglévő pending/failed sorokat dolgozza fel"
          >
            <Checkbox
              id="skip-discovery"
              checked={skipDiscovery}
              onCheckedChange={(checked) => setSkipDiscovery(checked === true)}
            />
            <Label htmlFor="skip-discovery">Keresés kihagyása</Label>
          </div>
          <Button
            onClick={() => startJob.mutate()}
            disabled={startJob.isPending || Boolean(activeJob) || !buildPersonaId}
          >
            {activeJob ? "Fut…" : "Build indítása"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>Run history</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => setStatusFilter("")}
              className={cn(
                "h-auto rounded-full px-2.5 py-1 text-xs font-medium",
                !statusFilter
                  ? "ring-2 ring-primary/40 ring-offset-1 ring-offset-background"
                  : "opacity-80 hover:opacity-100"
              )}
            >
              Összes
              <span className="tabular-nums text-[10px] opacity-70">{runs.length}</span>
            </Button>
            {RUN_STATUS_FILTERS.map((status) => (
              <RunStatusFilterChip
                key={status}
                status={status}
                count={statusCounts[status] ?? 0}
                active={statusFilter === status}
                onClick={() => toggleStatusFilter(status)}
              />
            ))}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {filteredRuns.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              {statusFilter ? `Nincs „${runStatusLabel(statusFilter)}” státuszú futás.` : "Még nem futott pipeline."}
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-4">Run</th>
                  {showAllPersonas ? <th className="py-2 pr-4">Persona</th> : null}
                  <th className="py-2 pr-4">Státusz</th>
                  <th className="py-2 pr-4">Indítva</th>
                  <th className="py-2 pr-4">Nettó idő</th>
                  <th className="py-2 pr-4" title="Mit indított a futás: keresés, feldolgozás, vagy mindkettő">
                    Mód
                  </th>
                  <th className="py-2 pr-4" title="Újonnan mentett források a discovery fázisban">
                    Talált
                  </th>
                  <th className="py-2 pr-4" title="Sikeresen feldolgozott források">
                    Feldolgozva
                  </th>
                  <th className="py-2 pr-4" title="Változatlan források, kihagyva">
                    Skip
                  </th>
                  <th className="py-2 pr-4" title="Knowledge unitok (run végén)">
                    Unitok
                  </th>
                  <th className="py-2 pr-4">Hibák</th>
                  <th className="py-2 pr-4" title="LLM API + Scrapfly becsült USD (api_usage_logs)">
                    Költség
                  </th>
                  <th className="py-2 pr-4">API hívás</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((run) => (
                  <RunTableRow
                    key={`${run.persona_id}-${run.run_id}`}
                    run={run}
                    personaLabel={personaLabels[run.persona_id] ?? run.persona_id}
                    showPersona={showAllPersonas}
                    activeJob={activeJobsByPersona.get(run.persona_id) ?? null}
                    onStop={(runId, personaId) => stopRunMutation.mutate({ runId, personaId })}
                    stopPending={stopRunMutation.isPending}
                  />
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
