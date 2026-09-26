import { NationalExplorer } from "@/components/national/NationalExplorer";
import { parseNationalFilters } from "@/lib/national/filters";
import { loadNationalExplorer } from "@/lib/national/server";
import type { NationalExplorerPayload } from "@/lib/national/types";

export const dynamic = "force-dynamic";

export default async function ExplorePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const raw = await searchParams;
  let initial: NationalExplorerPayload;
  try {
    const filters = parseNationalFilters(raw);
    initial = await loadNationalExplorer(filters);
  } catch (error) {
    const fallback = await loadNationalExplorer(parseNationalFilters({}));
    initial = {
      ...fallback,
      available: false as const,
      mode: "unavailable" as const,
      reason: `Invalid explorer URL (${error instanceof Error ? error.message : "invalid filters"}).`,
      projects: [],
      mapProjects: [],
      total: 0,
      locatedTotal: 0,
      unlocatedTotal: 0,
      mapTruncated: false,
    };
  }
  return <NationalExplorer initial={initial} />;
}
