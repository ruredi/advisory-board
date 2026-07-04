"use client";

import { useCallback, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "@/lib/icons";

import { SourceDetailPanel } from "@/components/dashboard/source-detail-panel";
import { SourceStatusChip } from "@/components/shared/source-status-chip";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { SourceItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

export function SourceDetailModal({
  open,
  onOpenChange,
  sources,
  selectedIndex,
  onSelectedIndexChange,
  personaLabels,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sources: SourceItem[];
  selectedIndex: number | null;
  onSelectedIndexChange: (index: number) => void;
  personaLabels: Record<string, string>;
}) {
  const current = selectedIndex !== null ? sources[selectedIndex] : null;
  const hasPrev = selectedIndex !== null && selectedIndex > 0;
  const hasNext = selectedIndex !== null && selectedIndex < sources.length - 1;

  const goPrev = useCallback(() => {
    if (selectedIndex !== null && selectedIndex > 0) {
      onSelectedIndexChange(selectedIndex - 1);
    }
  }, [onSelectedIndexChange, selectedIndex]);

  const goNext = useCallback(() => {
    if (selectedIndex !== null && selectedIndex < sources.length - 1) {
      onSelectedIndexChange(selectedIndex + 1);
    }
  }, [onSelectedIndexChange, selectedIndex, sources.length]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, goPrev, goNext]);

  const positionLabel =
    selectedIndex !== null && sources.length > 0
      ? `${selectedIndex + 1} / ${sources.length}${sources.length === 500 ? "+" : ""}`
      : "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(92vh,860px)] w-[min(calc(100vw-2rem),56rem)]">
        <DialogHeader className="space-y-3">
          <div className="flex items-start gap-2">
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              className="shrink-0"
              aria-label="Előző forrás"
              title="Előző forrás (←)"
              disabled={!hasPrev}
              onClick={goPrev}
            >
              <ChevronLeft className="size-4" />
            </Button>

            <div className="min-w-0 flex-1 space-y-1 text-center">
              <DialogTitle className="truncate text-base">
                {current?.source_title || current?.source_url || "Forrás részletei"}
              </DialogTitle>
              <DialogDescription className="flex flex-wrap items-center justify-center gap-2 text-xs">
                <span className="tabular-nums">{positionLabel}</span>
                {current ? <SourceStatusChip status={current.status} /> : null}
                {current && personaLabels[current.persona_id] ? (
                  <span>{personaLabels[current.persona_id]}</span>
                ) : null}
              </DialogDescription>
            </div>

            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              className="shrink-0"
              aria-label="Következő forrás"
              title="Következő forrás (→)"
              disabled={!hasNext}
              onClick={goNext}
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
          <p className="text-center text-[11px] text-muted-foreground">
            ← → billentyűkkel is lapozhatsz a szűrt listában
          </p>
        </DialogHeader>

        <DialogBody className={cn(!current && "py-8 text-center text-sm text-muted-foreground")}>
          {current ? (
            <SourceDetailPanel
              key={`${current.persona_id}-${current.id}`}
              personaId={current.persona_id}
              sourceId={current.id}
              personaLabel={personaLabels[current.persona_id]}
              summary={null}
              variant="plain"
            />
          ) : (
            "Nincs kiválasztott forrás."
          )}
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
