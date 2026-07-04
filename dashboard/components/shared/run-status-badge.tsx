import { Badge } from "@/components/ui/badge";
import { runStatusLabel, runStatusVariant } from "@/lib/run-status";

export function RunStatusBadge({ status }: { status: string }) {
  return <Badge variant={runStatusVariant(status)}>{runStatusLabel(status)}</Badge>;
}
