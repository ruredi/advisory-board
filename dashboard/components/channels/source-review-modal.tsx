"use client";

import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Loader } from "@/lib/icons";

import {
  ChannelTypeBadge,
  ChannelTypeIcon,
} from "@/components/channels/channel-type-icon";
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
import { discoverCandidates, submitReview } from "@/lib/api/client";
import type { SourceCandidateItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type ReviewStep = "discovering" | "candidates" | "manual" | "summary" | "error";

const USER_STEPS: { id: ReviewStep; label: string }[] = [
  { id: "discovering", label: "Keresés" },
  { id: "candidates", label: "Jelöltek" },
  { id: "manual", label: "Kézi linkek" },
  { id: "summary", label: "Összegzés" },
];

const MIN_DISCOVERY_MS = 700;

function formatDisplayUrl(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    const path = parsed.pathname === "/" ? "" : parsed.pathname;
    return `${parsed.hostname.replace(/^www\./, "")}${path}`;
  } catch {
    return url;
  }
}

function StepIndicator({ step }: { step: ReviewStep }) {
  const activeIndex =
    step === "error"
      ? 0
      : USER_STEPS.findIndex((item) => item.id === step);

  return (
    <div className="flex flex-wrap gap-2">
      {USER_STEPS.map((item, index) => {
        const done = step !== "error" && index < activeIndex;
        const active = index === activeIndex && step !== "summary";
        const failed = step === "error" && index === 0;
        return (
          <Badge
            key={item.id}
            variant={failed ? "destructive" : active ? "default" : done ? "secondary" : "outline"}
            className={cn(!active && !done && !failed && "opacity-50")}
          >
            {index + 1}. {item.label}
          </Badge>
        );
      })}
    </div>
  );
}

function CandidateRow({
  candidate,
  rejected,
  onToggleReject,
}: {
  candidate: SourceCandidateItem;
  rejected: boolean;
  onToggleReject: (checked: boolean) => void;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border p-3 text-sm transition-colors",
        rejected && "border-destructive/30 bg-destructive/5 opacity-80"
      )}
    >
      <Checkbox
        className="mt-2 shrink-0"
        checked={rejected}
        onCheckedChange={(checked) => onToggleReject(checked === true)}
        aria-label={`${candidate.index}. jelölt kizárása`}
      />
      <ChannelTypeIcon type={candidate.platform} size="lg" className="shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">[{candidate.index}]</span>
          <ChannelTypeBadge type={candidate.platform} />
          <span className="text-xs text-muted-foreground">
            conf {candidate.confidence.toFixed(2)}
          </span>
          <span className="text-xs text-muted-foreground">· {candidate.discovery_source}</span>
          {rejected ? <Badge variant="outline">kizárva</Badge> : null}
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
    </div>
  );
}

export function SourceReviewModal({
  personaId,
  open,
  onOpenChange,
}: {
  personaId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<ReviewStep>("discovering");
  const [candidates, setCandidates] = useState<SourceCandidateItem[]>([]);
  const [rejected, setRejected] = useState<Set<number>>(new Set());
  const [manualUrl, setManualUrl] = useState("");
  const [manualUrls, setManualUrls] = useState<string[]>([]);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [approvedCount, setApprovedCount] = useState(0);
  const [runToken, setRunToken] = useState(0);

  const submitMutation = useMutation({
    mutationFn: () =>
      submitReview(personaId, {
        rejected_indices: Array.from(rejected),
        manual_urls: manualUrls,
      }),
    onSuccess: (data) => {
      setApprovedCount(data.approved_count);
      setStep("summary");
      queryClient.invalidateQueries({ queryKey: ["candidates", personaId] });
      queryClient.invalidateQueries({ queryKey: ["channels", personaId] });
    },
    onError: (error) => {
      setSubmitError(error instanceof Error ? error.message : "Mentés sikertelen.");
    },
  });

  const runDiscovery = useCallback(async () => {
    setStep("discovering");
    setCandidates([]);
    setRejected(new Set());
    setManualUrl("");
    setManualUrls([]);
    setDiscoveryError(null);
    setSubmitError(null);
    setApprovedCount(0);

    const started = Date.now();
    try {
      const data = await discoverCandidates(personaId);
      const elapsed = Date.now() - started;
      if (elapsed < MIN_DISCOVERY_MS) {
        await new Promise((resolve) => setTimeout(resolve, MIN_DISCOVERY_MS - elapsed));
      }
      setCandidates(data);
      setStep("candidates");
    } catch (error) {
      const elapsed = Date.now() - started;
      if (elapsed < MIN_DISCOVERY_MS) {
        await new Promise((resolve) => setTimeout(resolve, MIN_DISCOVERY_MS - elapsed));
      }
      setDiscoveryError(error instanceof Error ? error.message : "Discovery sikertelen.");
      setStep("error");
    }
  }, [personaId]);

  useEffect(() => {
    if (!open) return;
    void runDiscovery();
  }, [open, personaId, runToken, runDiscovery]);

  const rejectedCount = rejected.size;
  const keptCount = Math.max(0, candidates.length - rejectedCount) + manualUrls.length;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Source review — {personaId}</DialogTitle>
          <DialogDescription>
            Social profil jelöltek ellenőrzése (ugyanaz a folyamat, mint a terminálban).
          </DialogDescription>
          <StepIndicator step={step} />
        </DialogHeader>

        <DialogBody className="space-y-4">
          {step === "discovering" ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <Loader className="size-8 animate-spin text-muted-foreground" />
              <p className="text-sm font-medium">1. lépés — jelöltek keresése…</p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Seed fájlok, persona config és hivatalos oldalak alapján. Ha még nincs source
                config, automatikusan létrehozzuk.
              </p>
            </div>
          ) : null}

          {step === "error" ? (
            <div className="space-y-3 py-6 text-center">
              <p role="alert" className="text-sm text-destructive">
                {discoveryError ?? "Discovery sikertelen."}
              </p>
              <p className="text-xs text-muted-foreground">
                Ha a backend nem fut, indítsd: <code className="font-mono">make api</code>
              </p>
            </div>
          ) : null}

          {step === "candidates" ? (
            <div className="space-y-2">
              <p className="text-sm font-medium">
                2. lépés — nyisd meg a linkeket böngészőben, majd pipáld ki a NEM övéket:
              </p>
              {candidates.length === 0 ? (
                <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
                  Nem találtunk social profil jelöltet. Ellenőrizd a persona configot (
                  <code className="text-xs">seed_link_files</code>,{" "}
                  <code className="text-xs">social_profiles</code>,{" "}
                  <code className="text-xs">watch_feeds</code>) az Advisor → Config fájlok
                  menüben — vagy add meg kézzel a következő lépésben.
                </div>
              ) : (
                <div className="space-y-2">
                  {candidates.map((candidate) => (
                    <CandidateRow
                      key={candidate.index}
                      candidate={candidate}
                      rejected={rejected.has(candidate.index)}
                      onToggleReject={(checked) => {
                        setRejected((prev) => {
                          const next = new Set(prev);
                          if (checked) next.add(candidate.index);
                          else next.delete(candidate.index);
                          return next;
                        });
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : null}

          {step === "manual" ? (
            <div className="space-y-4">
              <p className="text-sm font-medium">3. lépés — van még oldal, amit kihagytunk?</p>
              <p className="text-xs text-muted-foreground">
                Social profil (X, Instagram, Facebook, LinkedIn) vagy content csatorna (YouTube
                csatorna, Spotify, Apple Podcasts).
              </p>
              <div className="flex flex-wrap items-end gap-2">
                <div className="min-w-0 flex-1 space-y-1.5">
                  <Label htmlFor="manual-review-url" className="text-xs">
                    Link
                  </Label>
                  <Input
                    id="manual-review-url"
                    value={manualUrl}
                    onChange={(e) => setManualUrl(e.target.value)}
                    placeholder="https://x.com/…"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && manualUrl.trim()) {
                        e.preventDefault();
                        setManualUrls((prev) => [...prev, manualUrl.trim()]);
                        setManualUrl("");
                      }
                    }}
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  disabled={!manualUrl.trim()}
                  onClick={() => {
                    if (!manualUrl.trim()) return;
                    setManualUrls((prev) => [...prev, manualUrl.trim()]);
                    setManualUrl("");
                  }}
                >
                  Hozzáadás
                </Button>
              </div>
              {manualUrls.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {manualUrls.map((item) => (
                    <Badge key={item} variant="secondary" className="gap-1 pr-1">
                      {formatDisplayUrl(item)}
                      <button
                        type="button"
                        className="ml-1 rounded px-1 hover:bg-muted"
                        aria-label="Eltávolítás"
                        onClick={() => setManualUrls((prev) => prev.filter((url) => url !== item))}
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Nincs kézi link — üresen is menthető.
                </p>
              )}
              {submitError ? (
                <p role="alert" className="text-sm text-destructive">
                  {submitError}
                </p>
              ) : null}
            </div>
          ) : null}

          {step === "summary" ? (
            <div className="space-y-3 py-4 text-sm">
              <p className="font-medium text-green-600">4. lépés — review mentve.</p>
              <ul className="space-y-1 text-muted-foreground">
                <li>Jóváhagyott források: {approvedCount}</li>
                <li>Kizárt jelöltek: {rejectedCount}</li>
                <li>Kézi linkek: {manualUrls.length}</li>
              </ul>
            </div>
          ) : null}
        </DialogBody>

        <DialogFooter>
          {step === "discovering" ? (
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Mégse
            </Button>
          ) : null}

          {step === "error" ? (
            <>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Bezárás
              </Button>
              <Button type="button" onClick={() => setRunToken((token) => token + 1)}>
                Újrapróbálás
              </Button>
            </>
          ) : null}

          {step === "candidates" ? (
            <>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Mégse
              </Button>
              <Button type="button" onClick={() => setStep("manual")}>
                Tovább — kézi linkek
              </Button>
            </>
          ) : null}

          {step === "manual" ? (
            <>
              <Button type="button" variant="outline" onClick={() => setStep("candidates")}>
                Vissza
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setSubmitError(null);
                  submitMutation.mutate();
                }}
                disabled={submitMutation.isPending}
              >
                {submitMutation.isPending ? (
                  <>
                    <Loader className="size-4 animate-spin" />
                    Mentés…
                  </>
                ) : (
                  `Mentés (${keptCount} forrás)`
                )}
              </Button>
            </>
          ) : null}

          {step === "summary" ? (
            <Button type="button" onClick={() => onOpenChange(false)}>
              Bezárás
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
