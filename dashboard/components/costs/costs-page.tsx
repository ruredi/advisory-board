"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/shared/page-header";
import { MetricCard } from "@/components/shared/metric-card";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ALL_PERSONAS,
  fetchAllCostBreakdown,
  fetchAllCostSummary,
  fetchAllScrapflyCostSummary,
  fetchCostBreakdown,
  fetchCostSummary,
  fetchScrapflyCostSummary,
  fetchScrapflySubscription,
} from "@/lib/api/client";
import type { ScrapflySubscription } from "@/lib/api/types";
import { formatCredits, formatDateOnly, formatUsd } from "@/lib/format";
import { CHART_AXIS_PROPS, CHART_ACTIVE_BAR_PROPS, CHART_GRID_PROPS, CHART_TOOLTIP_PROPS, chartColor } from "@/lib/chart-theme";
import { cn } from "@/lib/utils";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

type UsageDisplayMode = "credits" | "usd";

function UsageProgress({
  subscription,
  mode,
  onModeChange,
}: {
  subscription: ScrapflySubscription;
  mode: UsageDisplayMode;
  onModeChange: (mode: UsageDisplayMode) => void;
}) {
  const used = mode === "credits" ? subscription.credits_used : subscription.usage_usd;
  const limit =
    mode === "credits"
      ? subscription.credits_limit
      : subscription.plan_price_usd > 0
        ? subscription.plan_price_usd
        : subscription.credits_limit * subscription.usd_per_credit;
  const ratio = limit > 0 ? Math.min(used / limit, 1) : 0;
  const percent = Math.round(ratio * 100);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-muted-foreground">Használat</span>
        <ButtonGroup>
          <Button
            type="button"
            size="xs"
            variant={mode === "credits" ? "secondary" : "outline"}
            onClick={() => onModeChange("credits")}
          >
            Credits
          </Button>
          <Button
            type="button"
            size="xs"
            variant={mode === "usd" ? "secondary" : "outline"}
            onClick={() => onModeChange("usd")}
          >
            $
          </Button>
        </ButtonGroup>
      </div>
      <div className="flex items-center justify-between text-sm tabular-nums">
        <span className="font-medium">
          {mode === "credits"
            ? `${formatCredits(used)} / ${formatCredits(limit)}`
            : `${formatUsd(used)} / ${formatUsd(limit)}`}
        </span>
        <span className="text-muted-foreground">{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            subscription.quota_reached ? "bg-destructive" : "bg-chart-1"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {mode === "credits"
          ? `${formatCredits(subscription.credits_remaining)} credit maradt`
          : `${formatUsd(Math.max(limit - used, 0))} maradt a havi keretből`}
      </p>
    </div>
  );
}

function BreakdownTable({
  rows,
  mode,
}: {
  rows: Array<{
    label: string;
    cost_usd: number;
    input_tokens: number;
    output_tokens: number;
    api_credits: number;
    call_count: number;
  }>;
  mode: "tokens" | "credits";
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4">Címke</th>
            <th className="py-2 pr-4">Költség</th>
            {mode === "credits" ? (
              <th className="py-2 pr-4">Credit</th>
            ) : (
              <th className="py-2 pr-4">Token in/out</th>
            )}
            <th className="py-2 pr-4">Hívások</th>
            <th className="py-2 pr-4">Átlag / hívás</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5} className="py-4 text-muted-foreground">
                Nincs adat a kiválasztott időszakra.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.label} className="border-b">
                <td className="py-2 pr-4">{row.label}</td>
                <td className="py-2 pr-4 tabular-nums">{formatUsd(row.cost_usd)}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {mode === "credits"
                    ? formatCredits(row.api_credits)
                    : `${row.input_tokens.toLocaleString("hu-HU")} / ${row.output_tokens.toLocaleString("hu-HU")}`}
                </td>
                <td className="py-2 pr-4">{row.call_count}</td>
                <td className="py-2 pr-4 tabular-nums">
                  {row.call_count > 0 ? formatUsd(row.cost_usd / row.call_count) : "–"}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function CostsPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const showAllPersonas = personaId === ALL_PERSONAS;
  const [groupBy, setGroupBy] = useState("provider");
  const [usageMode, setUsageMode] = useState<UsageDisplayMode>("usd");

  const subscriptionQuery = useQuery({
    queryKey: ["scrapfly-subscription"],
    queryFn: fetchScrapflySubscription,
    refetchInterval: 60000,
  });

  const summaryQuery = useQuery({
    queryKey: ["cost-summary", personaId],
    queryFn: () => (showAllPersonas ? fetchAllCostSummary() : fetchCostSummary(personaId)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 10000,
  });

  const scrapflyQuery = useQuery({
    queryKey: ["scrapfly-costs", personaId],
    queryFn: () => (showAllPersonas ? fetchAllScrapflyCostSummary(30) : fetchScrapflyCostSummary(personaId, 30)),
    enabled: showAllPersonas || Boolean(personaId),
    refetchInterval: 10000,
  });

  const breakdownQuery = useQuery({
    queryKey: ["cost-breakdown", personaId, groupBy],
    queryFn: () =>
      showAllPersonas
        ? fetchAllCostBreakdown(groupBy, 30, "scrapfly")
        : fetchCostBreakdown(personaId, groupBy, 30, "scrapfly"),
    enabled: showAllPersonas || Boolean(personaId),
  });

  const apiChartData = (breakdownQuery.data ?? []).map((item) => ({
    name: item.label,
    cost: item.cost_usd,
  }));

  const scrapflyDailyData = (scrapflyQuery.data?.daily ?? []).map((item) => ({
    name: item.day.slice(5),
    fullDay: item.day,
    credits: item.api_credits,
    cost: item.cost_usd,
    calls: item.call_count,
  }));

  const subscription = subscriptionQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Költségek"
        description="LLM API tokenek és Scrapfly credit költségek külön blokkban."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError
        error={
          summaryQuery.error ??
          scrapflyQuery.error ??
          breakdownQuery.error ??
          subscriptionQuery.error
        }
      />

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Scrapfly előfizetés</CardTitle>
            <p className="text-sm text-muted-foreground">
              Havi keret és lejárat — élő adat a Scrapfly account API-ból.
            </p>
          </div>
          {subscription ? (
            <div className="flex items-center gap-2">
              <Badge variant="secondary">{subscription.plan_name}</Badge>
              {subscription.quota_reached ? <Badge variant="destructive">Kvóta elérve</Badge> : null}
            </div>
          ) : null}
        </CardHeader>
        <CardContent>
          {subscriptionQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Előfizetés betöltése…</p>
          ) : subscription ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <UsageProgress
                subscription={subscription}
                mode={usageMode}
                onModeChange={setUsageMode}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground">Megújul</p>
                  <p className="font-medium">{formatDateOnly(subscription.period_end)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Havi díj</p>
                  <p className="font-medium tabular-nums">{formatUsd(subscription.plan_price_usd)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    {usageMode === "credits" ? "Maradék credit" : "Felhasználva (USD)"}
                  </p>
                  <p className="font-heading text-lg font-semibold tabular-nums">
                    {usageMode === "credits"
                      ? formatCredits(subscription.credits_remaining)
                      : formatUsd(subscription.usage_usd)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Párhuzamosság</p>
                  <p className="font-medium tabular-nums">
                    {subscription.concurrent_usage} / {subscription.concurrent_limit}
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <p className="text-xs text-muted-foreground">Projekt</p>
                  <p className="font-medium">{subscription.project_name}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Scrapfly előfizetés nem elérhető — ellenőrizd a SCRAPFLY_KEY env változót.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="LLM API — mai költség"
          value={formatUsd(summaryQuery.data?.today_api_usd ?? 0)}
          hint={`${summaryQuery.data?.today_api_calls ?? 0} hívás (Google, OpenAI)`}
        />
        <MetricCard
          label="Scrapfly — mai költség"
          value={formatUsd(summaryQuery.data?.today_scrapfly_usd ?? 0)}
          hint={`${formatCredits(summaryQuery.data?.today_scrapfly_credits ?? 0)} credit · ${summaryQuery.data?.today_scrapfly_calls ?? 0} scrape`}
        />
        <MetricCard
          label="Scrapfly — cost / scrape (ma)"
          value={
            scrapflyQuery.data?.today_cost_per_scrape != null
              ? formatUsd(scrapflyQuery.data.today_cost_per_scrape)
              : "–"
          }
          hint={
            scrapflyQuery.data?.today_calls
              ? `${scrapflyQuery.data.today_calls} scrape ma`
              : "Nincs mai scrape"
          }
        />
        <MetricCard
          label={showAllPersonas ? "Összesen (minden advisor)" : "Összesen (persona)"}
          value={formatUsd(summaryQuery.data?.total_usd ?? 0)}
          hint={`${summaryQuery.data?.total_calls ?? 0} hívás összesen`}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <MetricCard
          label="Scrapfly — cost / scrape (összesen)"
          value={
            scrapflyQuery.data?.total_cost_per_scrape != null
              ? formatUsd(scrapflyQuery.data.total_cost_per_scrape)
              : "–"
          }
          hint={`${formatCredits(scrapflyQuery.data?.total_credits ?? 0)} credit · ${scrapflyQuery.data?.total_calls ?? 0} scrape`}
        />
        <MetricCard
          label="Scrapfly — napi átlag (30 nap)"
          value={formatUsd(
            scrapflyDailyData.length > 0
              ? scrapflyDailyData.reduce((sum, row) => sum + row.cost, 0) / scrapflyDailyData.length
              : 0
          )}
          hint="Becsült napi költés az elmúlt 30 napból"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scrapfly — napi használat</CardTitle>
          <p className="text-sm text-muted-foreground">
            Credit, költség és scrape hívások napra bontva (utolsó 30 nap).
          </p>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={scrapflyDailyData}>
              <CartesianGrid {...CHART_GRID_PROPS} />
              <XAxis dataKey="name" {...CHART_AXIS_PROPS} />
              <YAxis
                yAxisId="credits"
                tickFormatter={(v) => formatCredits(Number(v))}
                width={70}
                {...CHART_AXIS_PROPS}
              />
              <YAxis
                yAxisId="cost"
                orientation="right"
                tickFormatter={(v) => `$${Number(v).toFixed(3)}`}
                width={60}
                {...CHART_AXIS_PROPS}
              />
              <Tooltip
                {...CHART_TOOLTIP_PROPS}
                formatter={(value, name) => {
                  const numeric = Number(value);
                  if (name === "cost") return formatUsd(numeric);
                  if (name === "credits") return `${formatCredits(numeric)} credit`;
                  return numeric;
                }}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as { fullDay?: string } | undefined;
                  return row?.fullDay ?? "";
                }}
              />
              <Bar
                yAxisId="credits"
                dataKey="credits"
                fill="var(--chart-1)"
                radius={4}
                name="credits"
                activeBar={CHART_ACTIVE_BAR_PROPS}
              />
              <Line
                yAxisId="cost"
                type="monotone"
                dataKey="cost"
                stroke="var(--chart-2)"
                strokeWidth={2}
                dot={false}
                name="cost"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scrapfly — műveletek</CardTitle>
        </CardHeader>
        <CardContent>
          <BreakdownTable rows={scrapflyQuery.data?.by_operation ?? []} mode="credits" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>LLM API bontás</CardTitle>
            <p className="text-sm text-muted-foreground">Google és OpenAI — token alapú költség.</p>
          </div>
          <Select value={groupBy} onValueChange={setGroupBy}>
            <SelectTrigger size="sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="provider">Provider</SelectItem>
              <SelectItem value="model">Modell</SelectItem>
              <SelectItem value="operation">Művelet</SelectItem>
              <SelectItem value="day">Nap</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={apiChartData}>
              <CartesianGrid {...CHART_GRID_PROPS} />
              <XAxis dataKey="name" {...CHART_AXIS_PROPS} />
              <YAxis tickFormatter={(v) => `$${Number(v).toFixed(3)}`} width={60} {...CHART_AXIS_PROPS} />
              <Tooltip
                {...CHART_TOOLTIP_PROPS}
                formatter={(value) => formatUsd(Number(value))}
              />
              <Bar dataKey="cost" radius={4} activeBar={CHART_ACTIVE_BAR_PROPS}>
                {apiChartData.map((entry, index) => (
                  <Cell key={entry.name} fill={chartColor(index)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>LLM API részletek</CardTitle>
        </CardHeader>
        <CardContent>
          <BreakdownTable rows={breakdownQuery.data ?? []} mode="tokens" />
        </CardContent>
      </Card>
    </div>
  );
}
