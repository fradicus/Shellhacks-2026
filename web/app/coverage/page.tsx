import { CoverageView } from "@/components/coverage/CoverageView";
import { ErrorState } from "@/components/ui";
import { getCoverage, getLatestRun, getSources } from "@/lib/data";
import { isUnavailable } from "@/lib/types";

export const metadata = { title: "Data quality · Common Ground" };

export default async function CoveragePage() {
  const [coverage, sources, latestRun] = await Promise.all([getCoverage(), getSources(), getLatestRun()]);
  if (isUnavailable(coverage) || isUnavailable(sources) || isUnavailable(latestRun)) {
    return (
      <main>
        <h1>Data quality</h1>
        <ErrorState />
      </main>
    );
  }
  return <CoverageView coverage={coverage} sources={sources} latestRun={latestRun} />;
}
