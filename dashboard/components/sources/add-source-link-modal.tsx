"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Link2, Loader } from "@/lib/icons";

import { ChannelTypeIcon } from "@/components/channels/channel-type-icon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { analyzeSourceLink, submitSourceLink, ALL_PERSONAS } from "@/lib/api/client";
import type { SourceLinkAnalyzeResponse, SourceLinkPersonaMatch } from "@/lib/api/types";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";
import { cn } from "@/lib/utils";

type Step = "input" | "preview" | "done" | "error";

const KIND_LABELS: Record<string, string> = {
  content: "Egyedi tartalom",
  content_channel: "Content csatorna",
  social_profile: "Social profil",
  unsupported: "Nem támogatott",
};

function formatDisplayUrl(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    const path = parsed.pathname === "/" ? "" : parsed.pathname;
    return `${parsed.hostname.replace(/^www\./, "")}${path}`;
  } catch {
    return url;
  }
}

function PersonaMatchRow({
  match,
  checked,
  onToggle,
}: {
  match: SourceLinkPersonaMatch;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition-colors",
        checked ? "border-primary bg-primary/5" : "hover:bg-muted/40"
      )}
    >
      <Checkbox checked={checked} onCheckedChange={(value) => onToggle(value === true)} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{match.display_name}</span>
          <Badge variant="outline" className="tabular-nums">
            {Math.round(match.confidence * 100)}%
          </Badge>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{match.signals.join(" · ")}</p>
      </div>
    </label>
  );
}

export function AddSourceLinkModal({
  open,
  onOpenChange,
  personaId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  personaId: string;
}) {
  const queryClient = useQueryClient();
  const { personas } = usePersonaOptions();
  const personaLabels = useMemo(
    () => Object.fromEntries(personas.map((persona) => [persona.persona_id, persona.display_name])),
    [personas]
  );
  const hintPersonaId = personaId === ALL_PERSONAS ? undefined : personaId;

  const [step, setStep] = useState<Step>("input");
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState<SourceLinkAnalyzeResponse | null>(null);
  const [selectedPersonas, setSelectedPersonas] = useState<Set<string>>(new Set());
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitSummary, setSubmitSummary] = useState<string[]>([]);

  const reset = () => {
    setStep("input");
    setUrl("");
    setAnalysis(null);
    setSelectedPersonas(new Set());
    setErrorMessage(null);
    setSubmitSummary([]);
  };

  useEffect(() => {
    if (!open) reset();
  }, [open]);

  const analyzeMutation = useMutation({
    mutationFn: () =>
      analyzeSourceLink({
        url: url.trim(),
        persona_id: hintPersonaId,
      }),
    onSuccess: (data) => {
      setAnalysis(data);
      const defaults = new Set(
        data.matched_personas.filter((item) => item.selected).map((item) => item.persona_id)
      );
      if (defaults.size === 0 && hintPersonaId) {
        defaults.add(hintPersonaId);
      }
      setSelectedPersonas(defaults);
      if (!data.processable) {
        setErrorMessage(data.message);
        setStep("error");
        return;
      }
      setErrorMessage(null);
      setStep("preview");
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "Elemzés sikertelen.");
      setStep("error");
    },
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      submitSourceLink({
        url: url.trim(),
        persona_ids: Array.from(selectedPersonas),
        process: true,
        persona_id: hintPersonaId,
      }),
    onSuccess: (data) => {
      const lines = data.results.map((item) => {
        const label = personaLabels[item.persona_id] ?? item.persona_id;
        return `${label}: ${item.message}${item.job_id ? " (feldolgozás elindítva)" : ""}`;
      });
      setSubmitSummary(lines);
      setStep("done");
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      queryClient.invalidateQueries({ queryKey: ["source-stats"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : "Beküldés sikertelen.");
      setStep("error");
    },
  });

  const togglePersona = (personaIdValue: string, checked: boolean) => {
    setSelectedPersonas((current) => {
      const next = new Set(current);
      if (checked) next.add(personaIdValue);
      else next.delete(personaIdValue);
      return next;
    });
  };

  const availableMatches = analysis?.matched_personas ?? [];
  const extraPersonas =
    hintPersonaId && !availableMatches.some((item) => item.persona_id === hintPersonaId)
      ? [
          {
            persona_id: hintPersonaId,
            display_name: personaLabels[hintPersonaId] ?? hintPersonaId,
            confidence: 0.99,
            signals: ["ui_hint"],
            selected: true,
          } satisfies SourceLinkPersonaMatch,
        ]
      : [];

  const autoChoices = [...availableMatches, ...extraPersonas];
  const personaChoices =
    autoChoices.length > 0
      ? autoChoices
      : personas.map(
          (persona): SourceLinkPersonaMatch => ({
            persona_id: persona.persona_id,
            display_name: persona.display_name,
            confidence: persona.persona_id === hintPersonaId ? 0.99 : 0.5,
            signals: persona.persona_id === hintPersonaId ? ["ui_hint"] : ["manual_pick"],
            selected: persona.persona_id === hintPersonaId,
          })
        );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="size-4" />
            Link hozzáadása
          </DialogTitle>
          <DialogDescription>
            Bármilyen tartalom link — a rendszer felismeri a típust és javasol advisor(ok)at.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="space-y-4">
          {step === "input" ? (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="source-link-url">URL</Label>
                <Input
                  id="source-link-url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://youtube.com/watch?v=…"
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && url.trim()) {
                      event.preventDefault();
                      analyzeMutation.mutate();
                    }
                  }}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                YouTube videó, podcast epizód, social poszt, cikk — vagy csatorna/profil link is lehet.
              </p>
            </div>
          ) : null}

          {step === "preview" && analysis ? (
            <div className="space-y-4">
              <div className="rounded-lg border p-3 text-sm">
                <div className="flex items-start gap-3">
                  <ChannelTypeIcon type={analysis.source_type} size="sm" className="mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{analysis.platform}</Badge>
                      <Badge variant="outline">{KIND_LABELS[analysis.kind] ?? analysis.kind}</Badge>
                    </div>
                    <p className="mt-2 font-medium">{analysis.title}</p>
                    <a
                      href={analysis.normalized_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex max-w-full items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <span className="truncate">{formatDisplayUrl(analysis.normalized_url)}</span>
                      <ExternalLink className="size-3 shrink-0 opacity-60" />
                    </a>
                    {analysis.message ? (
                      <p className="mt-2 text-xs text-muted-foreground">{analysis.message}</p>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Melyik advisor(ok)hoz tartozik?</p>
                {autoChoices.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Nem sikerült automatikusan illeszteni — válaszd ki kézzel az advisor(ok)at.
                  </p>
                ) : null}
                <div className="space-y-2">
                  {personaChoices.map((match) => (
                    <PersonaMatchRow
                      key={match.persona_id}
                      match={match}
                      checked={selectedPersonas.has(match.persona_id)}
                      onToggle={(checked) => togglePersona(match.persona_id, checked)}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : null}

          {step === "done" ? (
            <div className="space-y-2 text-sm">
              <p className="font-medium text-emerald-600">Link felvéve.</p>
              <ul className="space-y-1 text-muted-foreground">
                {submitSummary.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {step === "error" && errorMessage ? (
            <p role="alert" className="text-sm text-destructive">
              {errorMessage}
            </p>
          ) : null}
        </DialogBody>

        <DialogFooter>
          {step === "input" ? (
            <>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Mégse
              </Button>
              <Button
                type="button"
                onClick={() => analyzeMutation.mutate()}
                disabled={!url.trim() || analyzeMutation.isPending}
              >
                {analyzeMutation.isPending ? (
                  <>
                    <Loader className="size-4 animate-spin" />
                    Elemzés…
                  </>
                ) : (
                  "Elemzés"
                )}
              </Button>
            </>
          ) : null}

          {step === "preview" ? (
            <>
              <Button type="button" variant="outline" onClick={() => setStep("input")}>
                Vissza
              </Button>
              <Button
                type="button"
                onClick={() => submitMutation.mutate()}
                disabled={selectedPersonas.size === 0 || submitMutation.isPending}
              >
                {submitMutation.isPending ? (
                  <>
                    <Loader className="size-4 animate-spin" />
                    Felvétel…
                  </>
                ) : (
                  `Felvétel (${selectedPersonas.size} advisor)`
                )}
              </Button>
            </>
          ) : null}

          {step === "done" || step === "error" ? (
            <Button type="button" onClick={() => onOpenChange(false)}>
              Bezárás
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
