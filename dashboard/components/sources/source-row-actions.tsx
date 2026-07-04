"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArchiveRestore, Delete, Loader, Play } from "@/lib/icons";

import { Button } from "@/components/ui/button";
import { deleteSource, patchSource, processSource } from "@/lib/api/client";
import type { JobItem, SourceItem } from "@/lib/api/types";
import { SOURCE_ACTIVE_STATUSES } from "@/lib/source-status";
import { cn } from "@/lib/utils";

function canRestart(status: string): boolean {
  return status !== "pending" && !SOURCE_ACTIVE_STATUSES.includes(status);
}

function canProcess(status: string): boolean {
  return !SOURCE_ACTIVE_STATUSES.includes(status);
}

function patchSourceInListCache(
  queryClient: ReturnType<typeof useQueryClient>,
  personaId: string,
  sourceId: number,
  patch: Partial<SourceItem>
) {
  queryClient.setQueriesData<SourceItem[]>({ queryKey: ["sources"] }, (current) => {
    if (!current) return current;
    return current.map((item) =>
      item.persona_id === personaId && item.id === sourceId ? { ...item, ...patch } : item
    );
  });
}

export function SourceRowActions({
  source,
  disabled,
  onDeleted,
  onProcessStarted,
}: {
  source: SourceItem;
  disabled?: boolean;
  onDeleted?: () => void;
  onProcessStarted?: (job: JobItem) => void;
}) {
  const queryClient = useQueryClient();
  const personaId = source.persona_id;

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["sources"] }),
      queryClient.invalidateQueries({ queryKey: ["source-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["sources-with-memory"] }),
      queryClient.invalidateQueries({ queryKey: ["jobs"] }),
      queryClient.invalidateQueries({ queryKey: ["runs", personaId] }),
      source.id
        ? queryClient.invalidateQueries({ queryKey: ["source", personaId, source.id] })
        : Promise.resolve(),
    ]);
  };

  const restartMutation = useMutation({
    mutationFn: () => patchSource(personaId, source.id, "pending"),
    onSuccess: invalidate,
  });

  const processMutation = useMutation({
    mutationFn: () => processSource(personaId, source.id),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["sources"] });
      patchSourceInListCache(queryClient, personaId, source.id, {
        status: "fetching",
        error_message: null,
      });
    },
    onSuccess: async (job) => {
      onProcessStarted?.(job);
      await invalidate();
    },
    onError: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSource(personaId, source.id),
    onSuccess: () => {
      invalidate();
      onDeleted?.();
    },
  });

  const busy =
    disabled ||
    restartMutation.isPending ||
    processMutation.isPending ||
    deleteMutation.isPending;

  const showRestart = canRestart(source.status);
  const showProcess = canProcess(source.status);

  return (
    <div className="flex items-center justify-end gap-0.5" onClick={(event) => event.stopPropagation()}>
      {showRestart ? (
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          className="size-7 text-muted-foreground hover:text-foreground"
          title="Újraindítás (pending)"
          aria-label="Újraindítás"
          disabled={busy}
          onClick={() => restartMutation.mutate()}
        >
          {restartMutation.isPending ? (
            <Loader className="size-3.5 animate-spin" />
          ) : (
            <ArchiveRestore className="size-3.5" />
          )}
        </Button>
      ) : null}
      {showProcess ? (
        <Button
          type="button"
          size="icon-xs"
          variant="ghost"
          className={cn(
            "size-7 text-muted-foreground hover:text-foreground",
            source.status === "pending" && "text-primary hover:text-primary"
          )}
          title="Feldolgozás"
          aria-label="Feldolgozás"
          disabled={busy}
          onClick={() => processMutation.mutate()}
        >
          {processMutation.isPending ? (
            <Loader className="size-3.5 animate-spin" />
          ) : (
            <Play className="size-3.5" />
          )}
        </Button>
      ) : null}
      <Button
        type="button"
        size="icon-xs"
        variant="ghost"
        className="size-7 text-muted-foreground hover:text-destructive"
        title="Törlés"
        aria-label="Törlés"
        disabled={busy || SOURCE_ACTIVE_STATUSES.includes(source.status)}
        onClick={() => {
          const label = source.source_title || source.source_url;
          if (
            !window.confirm(
              `Biztosan törlöd ezt a forrást?\n\n${label}\n\nA knowledge unitok is törlődnek.`
            )
          ) {
            return;
          }
          deleteMutation.mutate();
        }}
      >
        {deleteMutation.isPending ? (
          <Loader className="size-3.5 animate-spin" />
        ) : (
          <Delete className="size-3.5" />
        )}
      </Button>
    </div>
  );
}
