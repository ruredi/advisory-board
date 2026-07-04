"use client";

import { useQuery } from "@tanstack/react-query";

import { MetricCard } from "@/components/shared/metric-card";
import {
  fetchAllCostSummary,
  fetchAllRuns,
  fetchAllSourceStats,
  fetchAllUnitStats,
  fetchCostSummary,
  fetchJobs,
  fetchRuns,
  fetchSourceStats,
  fetchUnitStats,
} from "@/lib/api/client";
import { formatUsd } from "@/lib/format";

export function DashboardHealthStrip({
  personaId,
  showAllPersonas,
}: {
  personaId: string;
  showAllPersonas: boolean;
}) {
  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: 5000,
  });
  const runsQuery = useQuery({
    queryKey: ["runs", personaId],
    queryFn: () => (showAllPersonas ? fetchAllRuns() : fetchRuns(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 5000,
  });
  const sourceStatsQuery = useQuery({
    queryKey: ["source-stats", personaId],
    queryFn: () => (showAllPersonas ? fetchAllSourceStats() : fetchSourceStats(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
  });
  const unitStatsQuery = useQuery({
    queryKey: ["unit-stats", personaId],
    queryFn: () => (showAllPersonas ? fetchAllUnitStats() : fetchUnitStats(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
  });
  const costQuery = useQuery({
    queryKey: ["cost-summary", personaId],
    queryFn: () => (showAllPersonas ? fetchAllCostSummary() : fetchCostSummary(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 10000,
  });

  const jobs = showAllPersonas
    ? (jobsQuery.data ?? [])
    : (jobsQuery.data ?? []).filter((job) => job.persona_id === personaId);
  const activeJob = jobs.find((job) => job.status === "running") ?? null;
  const lastRun = (runsQuery.data ?? [])[0] ?? null;

  const sourceStats = sourceStatsQuery.data;
  const indexed = sourceStats?.status_counts["indexed"] ?? 0;
  const failed = sourceStats?.status_counts["failed"] ?? 0;
  const total = sourceStats?.total ?? 0;

  const unitStats = unitStatsQuery.data;
  const strong = unitStats?.by_confidence["strong"] ?? 0;
  const strongRatio = unitStats && unitStats.total > 0 ? Math.round((strong / unitStats.total) * 100) : null;

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label="Futás"
        value={activeJob ? "fut" : lastRun ? lastRun.status : "nincs futás"}
        hint={
          activeJob
            ? (activeJob.log_tail.at(-1) ?? "…")
            : lastRun
              ? `Run #${lastRun.run_id}${showAllPersonas ? ` · ${lastRun.persona_id}` : ""}`
              : "Indíts egy buildet a Futások oldalon"
        }
        tone={activeJob ? "success" : lastRun?.status === "failed" ? "danger" : "default"}
        href="/runs"
      />
      <MetricCard
        label="Források"
        value={`${indexed}/${total}`}
        hint={failed > 0 ? `${failed} hibás` : "indexelve"}
        tone={failed > 0 ? "danger" : "default"}
        href="/sources"
      />
      <MetricCard
        label="Memória"
        value={(unitStats?.total ?? 0).toLocaleString("hu-HU")}
        hint={strongRatio !== null ? `${strongRatio}% strong` : "unit"}
        href="/memory"
      />
      <MetricCard
        label="Mai költség"
        value={costQuery.data ? formatUsd(costQuery.data.today_usd) : "–"}
        hint={costQuery.data ? `összesen ${formatUsd(costQuery.data.total_usd)}` : undefined}
        href="/costs"
      />
    </div>
  );
}
