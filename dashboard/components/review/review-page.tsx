"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";

import {
  ChannelTypeBadge,
  ChannelTypeIcon,
} from "@/components/channels/channel-type-icon";
import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { discoverCandidates, fetchCandidates, submitReview } from "@/lib/api/client";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";
import { cn } from "@/lib/utils";

function formatDisplayUrl(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    const path = parsed.pathname === "/" ? "" : parsed.pathname;
    return `${parsed.hostname.replace(/^www\./, "")}${path}`;
  } catch {
    return url;
  }
}

export function ReviewPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [rejected, setRejected] = useState<Set<number>>(new Set());
  const [manualUrl, setManualUrl] = useState("");
  const [manualUrls, setManualUrls] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const candidatesQuery = useQuery({
    queryKey: ["candidates", personaId],
    queryFn: () => fetchCandidates(personaId),
    enabled: Boolean(personaId),
  });

  const discoverMutation = useMutation({
    mutationFn: () => discoverCandidates(personaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["candidates", personaId] }),
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      submitReview(personaId, {
        rejected_indices: Array.from(rejected),
        manual_urls: manualUrls,
      }),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Source review"
        description="Social profil jelöltek approve/reject."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={candidatesQuery.error} />

      <div className="flex gap-2">
        <Button variant="outline" onClick={() => discoverMutation.mutate()} disabled={discoverMutation.isPending}>
          Discovery indítása
        </Button>
        <Button onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending}>
          Review mentése
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle>Jelöltek</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {(candidatesQuery.data ?? []).map((candidate) => {
            const isRejected = rejected.has(candidate.index);
            return (
              <label
                key={candidate.index}
                className={cn(
                  "flex cursor-pointer gap-3 rounded-lg border p-4 text-sm transition-colors hover:bg-muted/30",
                  isRejected && "opacity-60"
                )}
              >
                <input
                  type="checkbox"
                  className="mt-3 shrink-0"
                  checked={isRejected}
                  onChange={(e) => {
                    setRejected((prev) => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(candidate.index);
                      else next.delete(candidate.index);
                      return next;
                    });
                  }}
                />
                <ChannelTypeIcon type={candidate.platform} size="lg" className="shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <ChannelTypeBadge type={candidate.platform} />
                    <span className="text-xs text-muted-foreground">
                      conf {candidate.confidence.toFixed(2)}
                    </span>
                    {isRejected ? <Badge variant="outline">kizárva</Badge> : null}
                  </div>
                  <a
                    href={candidate.url}
                    className="mt-1 inline-flex max-w-full items-center gap-1 text-primary hover:underline"
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <span className="truncate">{formatDisplayUrl(candidate.url)}</span>
                    <ExternalLink className="size-3 shrink-0 opacity-60" />
                  </a>
                  <p className="mt-1 text-xs text-muted-foreground">{candidate.signals.join(", ")}</p>
                </div>
              </label>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Manuális URL</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <input
            value={manualUrl}
            onChange={(e) => setManualUrl(e.target.value)}
            placeholder="https://x.com/..."
            className="min-w-72 rounded-md border bg-background px-3 py-2 text-sm"
          />
          <Button
            variant="outline"
            onClick={() => {
              if (!manualUrl) return;
              setManualUrls((prev) => [...prev, manualUrl]);
              setManualUrl("");
            }}
          >
            Hozzáadás
          </Button>
          {manualUrls.map((item) => (
            <Badge key={item} variant="secondary">{item}</Badge>
          ))}
        </CardContent>
      </Card>

      {submitMutation.isSuccess ? (
        <p className="text-sm text-green-600">Review mentve.</p>
      ) : null}
    </div>
  );
}
