"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createJob,
  fetchJobs,
  fetchRun,
  fetchRunEvents,
  fetchRuns,
  stopJob,
} from "@/lib/api/client";
import type { JobItem } from "@/lib/api/types";

function jobMode(command: string[]): "discovery" | "process" | "other" {
  const args = command.join(" ");
  if (args.includes("--discover-only")) return "discovery";
  if (args.includes("--skip-discovery")) return "process";
  return "other";
}

export function useSourceDiscovery(personaId: string, onlyPlatform: string) {
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data ?? [];
      const tracked = trackedJobId
        ? jobs.find((item) => item.job_id === trackedJobId)
        : null;
      const runningForPersona = personaId
        ? jobs.some((item) => item.persona_id === personaId && item.status === "running")
        : jobs.some((item) => item.status === "running");
      return tracked?.status === "running" || runningForPersona ? 2000 : false;
    },
  });

  const personaJobs = useMemo(
    () => (jobsQuery.data ?? []).filter((job) => job.persona_id === personaId),
    [jobsQuery.data, personaId]
  );

  const trackedJob: JobItem | null =
    personaJobs.find((job) => job.job_id === trackedJobId) ??
    personaJobs.find((job) => job.status === "running") ??
    null;

  const trackedMode = trackedJob ? jobMode(trackedJob.command) : null;
  const isRunning = trackedJob?.status === "running";
  const isDiscoverOnlyJob = trackedMode === "discovery";
  const isProcessJob = trackedMode === "process";
  const isFinished =
    trackedJob !== null &&
    trackedJob.status !== "running" &&
    trackedJob.job_id === trackedJobId;
  const showProgress = Boolean(
    trackedJob && (isRunning || isFinished) && (isDiscoverOnlyJob || isProcessJob)
  );

  useEffect(() => {
    if (!trackedJobId && trackedJob?.status === "running") {
      setTrackedJobId(trackedJob.job_id);
    }
  }, [trackedJobId, trackedJob?.job_id, trackedJob?.status]);

  const runsQuery = useQuery({
    queryKey: ["runs", personaId],
    queryFn: () => fetchRuns(personaId),
    enabled: Boolean(personaId),
    refetchInterval: isRunning ? 2000 : false,
  });

  const relevantRun =
    (runsQuery.data ?? []).find((run) => run.status === "running") ??
    (runsQuery.data ?? [])[0] ??
    null;

  const runDetailQuery = useQuery({
    queryKey: ["run", personaId, relevantRun?.run_id],
    queryFn: () => fetchRun(personaId, relevantRun!.run_id),
    enabled: Boolean(personaId && relevantRun && showProgress),
    refetchInterval: isRunning ? 2000 : false,
  });

  const eventsQuery = useQuery({
    queryKey: ["run-events", personaId, relevantRun?.run_id],
    queryFn: () => fetchRunEvents(personaId, relevantRun!.run_id, 0, 500),
    enabled: Boolean(personaId && relevantRun && showProgress),
    refetchInterval: isRunning ? 2000 : false,
  });

  const recentEvents = useMemo(() => eventsQuery.data ?? [], [eventsQuery.data]);

  const invalidateAfterJob = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
    queryClient.invalidateQueries({ queryKey: ["runs", personaId] });
    queryClient.invalidateQueries({ queryKey: ["sources", personaId] });
    queryClient.invalidateQueries({ queryKey: ["source-stats", personaId] });
    queryClient.invalidateQueries({ queryKey: ["sources-with-memory", personaId] });
  };

  const startDiscovery = useMutation({
    mutationFn: (discoveryLimit: number) =>
      createJob({
        persona_id: personaId,
        kind: "build",
        only_platform: onlyPlatform || null,
        skip_discovery: false,
        discover_only: true,
        discovery_limit: discoveryLimit,
      }),
    onSuccess: (job) => {
      setTrackedJobId(job.job_id);
      invalidateAfterJob();
    },
  });

  const startProcessing = useMutation({
    mutationFn: (processLimit: number) =>
      createJob({
        persona_id: personaId,
        kind: "build",
        only_platform: onlyPlatform || null,
        skip_discovery: true,
        limit: processLimit === 0 ? null : processLimit,
      }),
    onSuccess: (job) => {
      setTrackedJobId(job.job_id);
      invalidateAfterJob();
    },
  });

  const stopJobRun = useMutation({
    mutationFn: (jobId: string) => stopJob(jobId),
    onSuccess: invalidateAfterJob,
  });

  const trackJob = (jobId: string) => {
    setTrackedJobId(jobId);
    invalidateAfterJob();
  };

  useEffect(() => {
    if (isFinished && trackedJob?.status === "succeeded") {
      invalidateAfterJob();
    }
  }, [isFinished, trackedJob?.status, personaId, queryClient]);

  return {
    trackedJob,
    relevantRun,
    runDetail: runDetailQuery.data,
    recentEvents,
    isRunning,
    isDiscoverOnlyJob,
    isProcessJob,
    isFinished,
    showProgress,
    startDiscovery,
    startProcessing,
    stopDiscovery: stopJobRun,
    stopProcessing: stopJobRun,
    trackJob,
  };
}
