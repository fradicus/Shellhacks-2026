import { HistoryView, type HistoryParams } from "@/components/history/HistoryView";
import { ErrorState } from "@/components/ui";
import { loadHistory } from "@/lib/history/server";

export const dynamic = "force-dynamic";

export const metadata = { title: "History · GridBridge" };

const KEYS = ["origin", "project", "from", "to", "at", "show", "source", "q"] as const;

export default async function HistoryPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const [data, query] = await Promise.all([loadHistory(), searchParams]);
  if (!data.legacyAvailable && !data.national.available) {
    return (
      <main>
        <h1>History</h1>
        <ErrorState />
      </main>
    );
  }
  // Only the first value of each known parameter, bounded; the view validates each one again.
  const initial = Object.fromEntries(
    KEYS.map((k) => {
      const v = query[k];
      const first = Array.isArray(v) ? v[0] : v;
      return [k, first ? first.slice(0, 200) : null];
    }),
  ) as HistoryParams;
  return <HistoryView data={data} initial={initial} />;
}
