import { sourceStatusMeta } from "@/lib/source-status";
import { cn } from "@/lib/utils";

export function SourceStatusChip({ status, className }: { status: string; className?: string }) {
  const meta = sourceStatusMeta(status);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        meta.chipClass,
        className
      )}
    >
      <span className={cn("size-1.5 rounded-full", meta.dotClass)} aria-hidden />
      {meta.label}
    </span>
  );
}
