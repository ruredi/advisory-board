import { AdvisorsPageClient } from "@/components/advisors/advisors-page";
import { parseAdvisorTab } from "@/lib/advisor-tabs";

export default async function AdvisorsPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const { tab } = await searchParams;
  return <AdvisorsPageClient initialTab={parseAdvisorTab(tab)} />;
}
