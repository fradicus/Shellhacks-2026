import { AssistantExplorer } from "@/components/assistant/AssistantExplorer";
import { parseNationalFilters } from "@/lib/national/filters";
import { loadNationalSummaries } from "@/lib/national/server";
import type { NationalSummaryPayload } from "@/lib/national/types";

export const dynamic = "force-dynamic";
export const metadata = { title: "Common Ground assistant · GridBridge" };

export default async function AssistantPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  let initial: NationalSummaryPayload;
  try {
    initial = await loadNationalSummaries(parseNationalFilters(await searchParams));
  } catch (error) {
    const reference = await loadNationalSummaries(parseNationalFilters({}));
    initial = {
      ...reference, available: false, mode: "unavailable", projects: [], mapProjects: [],
      total: 0, locatedTotal: 0, unlocatedTotal: 0, mapTruncated: false,
      reason: `The URL contains unsupported filters (${error instanceof Error ? error.message : "invalid filters"}). Reset the filters to continue.`,
    };
  }
  return <AssistantExplorer initial={initial} />;
}
