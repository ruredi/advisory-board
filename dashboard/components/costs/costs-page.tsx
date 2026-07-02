"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCostBreakdown, fetchCostSummary } from "@/lib/api/client";
import { formatUsd } from "@/lib/format";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

export function CostsPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [groupBy, setGroupBy] = useState("provider");

  const summaryQuery = useQuery({
    queryKey: ["cost-summary", personaId],
    queryFn: () => fetchCostSummary(personaId),
    enabled: Boolean(personaId),
    refetchInterval: 10000,
  });

  const breakdownQuery = useQuery({
    queryKey: ["cost-breakdown", personaId, groupBy],
    queryFn: () => fetchCostBreakdown(personaId, groupBy, 30),
    enabled: Boolean(personaId),
  });

  const chartData = (breakdownQuery.data ?? []).map((item) => ({
    name: item.label,
    cost: item.cost_usd,
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Költségek"
        description="API költségek provider, modell és nap szerint."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={summaryQuery.error ?? breakdownQuery.error} />

      <div className="grid gap-4 sm:grid-cols-2">
        <Card size="sm">
          <CardContent>
            <p className="text-xs text-muted-foreground">Mai költség</p>
            <p className="font-heading text-xl font-semibold tabular-nums">
              {formatUsd(summaryQuery.data?.today_usd ?? 0)}
            </p>
            <p className="text-xs text-muted-foreground">{summaryQuery.data?.today_calls ?? 0} hívás</p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent>
            <p className="text-xs text-muted-foreground">Összesen</p>
            <p className="font-heading text-xl font-semibold tabular-nums">
              {formatUsd(summaryQuery.data?.total_usd ?? 0)}
            </p>
            <p className="text-xs text-muted-foreground">{summaryQuery.data?.total_calls ?? 0} hívás</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Bontás</CardTitle>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value)}
            className="rounded-md border bg-background px-3 py-1.5 text-sm"
          >
            <option value="provider">Provider</option>
            <option value="model">Modell</option>
            <option value="operation">Művelet</option>
            <option value="day">Nap</option>
          </select>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => `$${Number(v).toFixed(3)}`} width={60} />
              <Tooltip formatter={(value) => formatUsd(Number(value))} />
              <Bar dataKey="cost" fill="hsl(var(--primary))" radius={4} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Részletek</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4">Címke</th>
                <th className="py-2 pr-4">Költség</th>
                <th className="py-2 pr-4">Token in/out</th>
                <th className="py-2 pr-4">Hívások</th>
              </tr>
            </thead>
            <tbody>
              {(breakdownQuery.data ?? []).map((row) => (
                <tr key={row.label} className="border-b">
                  <td className="py-2 pr-4">{row.label}</td>
                  <td className="py-2 pr-4 tabular-nums">{formatUsd(row.cost_usd)}</td>
                  <td className="py-2 pr-4 tabular-nums">{row.input_tokens} / {row.output_tokens}</td>
                  <td className="py-2 pr-4">{row.call_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
