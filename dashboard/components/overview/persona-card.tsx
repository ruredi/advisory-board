import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { PersonaOverview } from "@/lib/api/types";
import { formatDateTime, formatUsd } from "@/lib/format";

const STATUS_LABELS: Record<string, string> = {
  pending: "várakozó",
  fetching: "letöltés",
  fetched: "letöltve",
  processing: "feldolgozás",
  processed: "feldolgozva",
  extracting: "kinyerés",
  indexed: "indexelve",
  failed: "hibás",
  skipped: "kihagyva",
};

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "failed") return "destructive";
  if (status === "indexed") return "default";
  return "secondary";
}

function ActiveRunSection({ overview }: { overview: PersonaOverview }) {
  const run = overview.active_run;
  if (!run) {
    return null;
  }
  const pendingEntries = Object.entries(run.pending_by_platform);
  return (
    <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          <span
            aria-hidden
            className="size-2 animate-pulse rounded-full bg-primary motion-reduce:animate-none"
          />
          Aktív run #{run.run_id}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatUsd(run.cost_run_usd)}
        </span>
      </div>
      {run.current_title ? (
        <p className="text-sm">
          {run.current_platform ? (
            <span className="font-medium">[{run.current_platform}] </span>
          ) : null}
          {run.current_title}
          {run.current_stage ? (
            <span className="text-muted-foreground"> — {run.current_stage}</span>
          ) : null}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          {run.latest_stage === "discovery" ? "Discovery fut…" : "Várakozás forrásra…"}
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        kész {run.done_count} · hiba {run.error_count} · kihagyva {run.skip_count}
      </p>
      {pendingEntries.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Várólista:{" "}
          {pendingEntries.map(([platform, count]) => `${platform} ${count}`).join(" · ")}
        </p>
      ) : null}
    </div>
  );
}

export function PersonaCard({ overview }: { overview: PersonaOverview }) {
  const statuses = Object.entries(overview.source_status_counts).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>{overview.display_name}</CardTitle>
        <CardDescription>
          {overview.source_total} forrás · {overview.unit_count} knowledge unit
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ActiveRunSection overview={overview} />

        <div className="flex flex-wrap gap-1.5">
          {statuses.length > 0 ? (
            statuses.map(([status, count]) => (
              <Badge key={status} variant={statusVariant(status)}>
                {STATUS_LABELS[status] ?? status}: {count}
              </Badge>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">Még nincs forrás.</p>
          )}
        </div>

        <Separator />

        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Mai költség</dt>
          <dd className="text-right font-medium tabular-nums">
            {formatUsd(overview.cost.today_usd)}
          </dd>
          <dt className="text-muted-foreground">Összköltség</dt>
          <dd className="text-right font-medium tabular-nums">
            {formatUsd(overview.cost.total_usd)}
          </dd>
          <dt className="text-muted-foreground">Utolsó run</dt>
          <dd className="text-right">
            {overview.last_run
              ? formatDateTime(overview.last_run.started_at)
              : "még nem futott"}
          </dd>
          {overview.last_run ? (
            <>
              <dt className="text-muted-foreground">Run eredmény</dt>
              <dd className="text-right text-muted-foreground">
                {overview.last_run.finished_at
                  ? `${overview.last_run.sources_processed} forrás · ${overview.last_run.units_created} unit`
                  : "folyamatban"}
              </dd>
            </>
          ) : null}
        </dl>
      </CardContent>
    </Card>
  );
}
