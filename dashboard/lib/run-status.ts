export const RUN_STATUS_FILTERS = ["running", "finished", "aborted", "interrupted"] as const;

export type RunStatusFilter = (typeof RUN_STATUS_FILTERS)[number];

export function runStatusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "failed" || status === "error" || status === "interrupted" || status === "aborted") {
    return "destructive";
  }
  if (status === "running") return "default";
  return "secondary";
}

export function runStatusLabel(status: string): string {
  if (status === "running") return "Fut";
  if (status === "finished") return "Kész";
  if (status === "aborted") return "Leállt (hiba)";
  if (status === "interrupted") return "Megszakítva";
  return status;
}
