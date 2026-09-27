import { AssistantExplorer } from "@/components/assistant/AssistantExplorer";
import { parseNationalFilters } from "@/lib/national/filters";
import { loadNationalExplorer } from "@/lib/national/server";
import type { NationalExplorerPayload } from "@/lib/national/types";

export const dynamic = "force-dynamic";
export const metadata = { title: "App control preview · GridBridge" };

export default async function AssistantPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  let initial: NationalExplorerPayload;
  try {
    initial = await loadNationalExplorer(parseNationalFilters(await searchParams));
  } catch {
    const reference = await loadNationalExplorer(parseNationalFilters({}));
    initial = {
      ...reference, available: false, mode: "unavailable", projects: [], mapProjects: [],
      total: 0, locatedTotal: 0, unlocatedTotal: 0, mapTruncated: false,
      reason: "The URL contains unsupported filters. Reset the filters to continue.",
    };
  }
  return <AssistantExplorer initial={initial} />;
}
