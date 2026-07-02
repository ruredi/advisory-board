import { RunDetailClient } from "@/components/runs/run-detail";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <RunDetailClient runId={Number(id)} />;
}
