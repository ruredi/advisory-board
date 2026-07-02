"use client";

import { PersonaCard } from "@/components/overview/persona-card";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { PersonaOverview } from "@/lib/api/types";
import { formatUsd } from "@/lib/format";
import { usePersonaOverviews, usePersonas } from "@/lib/hooks/use-personas";

function PersonaCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  );
}

function TotalsBar({ overviews }: { overviews: PersonaOverview[] }) {
  const todayUsd = overviews.reduce((sum, o) => sum + o.cost.today_usd, 0);
  const totalUsd = overviews.reduce((sum, o) => sum + o.cost.total_usd, 0);
  const activeRuns = overviews.filter((o) => o.active_run !== null).length;

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <Card size="sm">
        <CardContent>
          <p className="text-xs text-muted-foreground">Mai költség (összes persona)</p>
          <p className="font-heading text-xl font-semibold tabular-nums">
            {formatUsd(todayUsd)}
          </p>
        </CardContent>
      </Card>
      <Card size="sm">
        <CardContent>
          <p className="text-xs text-muted-foreground">Összköltség</p>
          <p className="font-heading text-xl font-semibold tabular-nums">
            {formatUsd(totalUsd)}
          </p>
        </CardContent>
      </Card>
      <Card size="sm">
        <CardContent>
          <p className="text-xs text-muted-foreground">Aktív run</p>
          <p className="font-heading text-xl font-semibold tabular-nums">{activeRuns}</p>
        </CardContent>
      </Card>
    </div>
  );
}

export function OverviewDashboard() {
  const personasQuery = usePersonas();
  const personaIds = (personasQuery.data ?? []).map((p) => p.persona_id);
  const overviewQueries = usePersonaOverviews(personaIds);

  if (personasQuery.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Nem sikerült betölteni a personákat. Fut az API a 8100-as porton?
      </p>
    );
  }

  if (personasQuery.isPending) {
    return (
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <PersonaCardSkeleton />
        <PersonaCardSkeleton />
      </div>
    );
  }

  if (personaIds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nincs persona konfigurálva. Adj hozzá egy YAML-t a{" "}
        <code className="font-mono text-xs">memory_builder/config/personas/</code>{" "}
        mappához.
      </p>
    );
  }

  const loadedOverviews = overviewQueries
    .map((query) => query.data)
    .filter((data): data is PersonaOverview => data !== undefined);

  return (
    <div className="space-y-6">
      {loadedOverviews.length > 0 ? <TotalsBar overviews={loadedOverviews} /> : null}
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {personaIds.map((personaId, index) => {
          const query = overviewQueries[index];
          if (query.isPending) {
            return <PersonaCardSkeleton key={personaId} />;
          }
          if (query.isError || !query.data) {
            return (
              <Card key={personaId}>
                <CardContent>
                  <p role="alert" className="text-sm text-destructive">
                    {personaId}: nem sikerült betölteni az adatokat.
                  </p>
                </CardContent>
              </Card>
            );
          }
          return <PersonaCard key={personaId} overview={query.data} />;
        })}
      </div>
    </div>
  );
}
