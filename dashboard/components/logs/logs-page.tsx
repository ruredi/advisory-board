"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchLogs } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

export function LogsPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [stage, setStage] = useState("");

  const logsQuery = useQuery({
    queryKey: ["logs", personaId, stage],
    queryFn: () => fetchLogs(personaId, stage ? { stage } : {}),
    enabled: Boolean(personaId),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Logok"
        description="Pipeline események élő tail."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={logsQuery.error} />

      <div className="flex gap-3">
        <select
          value={stage}
          onChange={(e) => setStage(e.target.value)}
          className="rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value="">Minden stage</option>
          <option value="source_error">source_error</option>
          <option value="source_done">source_done</option>
          <option value="source_start">source_start</option>
          <option value="discovery">discovery</option>
        </select>
      </div>

      <Card>
        <CardHeader><CardTitle>Események</CardTitle></CardHeader>
        <CardContent className="max-h-[40rem] space-y-2 overflow-y-auto font-mono text-xs">
          {(logsQuery.data ?? []).map((event) => (
            <div
              key={event.id}
              className={`rounded border px-2 py-1 ${event.stage === "source_error" ? "border-destructive/40 bg-destructive/5" : ""}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>
                <Badge variant={event.stage === "source_error" ? "destructive" : "secondary"}>{event.stage}</Badge>
                {event.run_id ? <span>run #{event.run_id}</span> : null}
              </div>
              <p className="mt-1">{event.message}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
