export interface SourceStatusMeta {
  label: string;
  chipClass: string;
  dotClass: string;
}

export const SOURCE_STATUS_META: Record<string, SourceStatusMeta> = {
  pending: {
    label: "várakozó",
    chipClass: "bg-amber-500/10 text-amber-700 border-amber-500/25 dark:text-amber-400",
    dotClass: "bg-amber-500",
  },
  fetching: {
    label: "letöltés",
    chipClass: "bg-blue-500/10 text-blue-700 border-blue-500/25 dark:text-blue-400",
    dotClass: "bg-blue-500 animate-pulse",
  },
  fetched: {
    label: "letöltve",
    chipClass: "bg-blue-500/10 text-blue-700 border-blue-500/25 dark:text-blue-400",
    dotClass: "bg-blue-500",
  },
  processing: {
    label: "feldolgozás",
    chipClass: "bg-sky-500/10 text-sky-700 border-sky-500/25 dark:text-sky-400",
    dotClass: "bg-sky-500 animate-pulse",
  },
  processed: {
    label: "feldolgozva",
    chipClass: "bg-sky-500/10 text-sky-700 border-sky-500/25 dark:text-sky-400",
    dotClass: "bg-sky-500",
  },
  extracting: {
    label: "kinyerés",
    chipClass: "bg-violet-500/10 text-violet-700 border-violet-500/25 dark:text-violet-400",
    dotClass: "bg-violet-500 animate-pulse",
  },
  indexed: {
    label: "indexelve",
    chipClass: "bg-emerald-500/10 text-emerald-700 border-emerald-500/25 dark:text-emerald-400",
    dotClass: "bg-emerald-500",
  },
  failed: {
    label: "hibás",
    chipClass: "bg-red-500/10 text-red-700 border-red-500/25 dark:text-red-400",
    dotClass: "bg-red-500",
  },
  skipped: {
    label: "kihagyva",
    chipClass: "bg-zinc-500/10 text-zinc-600 border-zinc-500/25 dark:text-zinc-400",
    dotClass: "bg-zinc-400",
  },
};

export const SOURCE_STATUS_ORDER = [
  "indexed",
  "pending",
  "fetching",
  "fetched",
  "processing",
  "processed",
  "extracting",
  "failed",
  "skipped",
];

/** Statuses where the pipeline is actively working on the source right now. */
export const SOURCE_ACTIVE_STATUSES = ["fetching", "processing", "extracting"];

export function sourceStatusMeta(status: string): SourceStatusMeta {
  return (
    SOURCE_STATUS_META[status] ?? {
      label: status,
      chipClass: "bg-muted text-muted-foreground border-border",
      dotClass: "bg-muted-foreground",
    }
  );
}

export function sortSourceStatusEntries(counts: Record<string, number>): [string, number][] {
  return Object.entries(counts).sort(([a], [b]) => {
    const ia = SOURCE_STATUS_ORDER.indexOf(a);
    const ib = SOURCE_STATUS_ORDER.indexOf(b);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}
