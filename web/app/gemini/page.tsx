import { Workbench, type Card } from "@/components/gemini/Workbench";
import { ErrorState } from "@/components/ui";
import { getBriefs, getExtractions, getProjects, getSources } from "@/lib/data";
import { isUnavailable, type Project } from "@/lib/types";

export const metadata = { title: "Gemini workbench · Common Ground" };

/** F01's deterministic parse under F03's field names, so both columns line up. */
function deterministic(p: Project): Record<string, unknown> {
  const raw = p as unknown as Record<string, unknown>;
  const filed = (p.filed_endpoints ?? (raw.endpoints as { name?: string; confidence?: string }[] | undefined) ?? [])
    .filter((e) => !("confidence" in e))
    .map((e) => e.name);
  return {
    project_id: p.native_id,
    name: p.name,
    description: p.description ?? null,
    need: p.need ?? null,
    status: p.status ?? null,
    in_service_raw: p.in_service.raw,
    total_cost: p.cost_usd ?? null,
    yearly_spend: raw.yearly_spend ?? null,
    endpoints: filed,
    voltage_kv: raw.voltages_kv ?? null,
  };
}

export default async function GeminiPage() {
  const [extractions, projects, sources, briefs] = await Promise.all([
    getExtractions(),
    getProjects(),
    getSources(),
    getBriefs(),
  ]);
  if (isUnavailable(extractions) || isUnavailable(projects) || isUnavailable(sources) || isUnavailable(briefs)) {
    return (
      <main>
        <h1>Gemini workbench</h1>
        <ErrorState />
      </main>
    );
  }
  // DESC cards only: Georgia pages are never sent to Gemini or shown beyond project names (decision D2).
  const cards: Card[] = projects
    .filter((p) => p.utility === "DESC" && p.source.page)
    .map((p) => ({
      key: `${p.source.source_id}#${p.source.page}`,
      sourceId: p.source.source_id,
      page: p.source.page!,
      projectKey: p.project_key,
      name: p.name,
      rawText: p.raw_text ?? null,
      flags: p.quality_flags ?? [],
      deterministic: deterministic(p),
    }))
    .sort((a, b) => a.sourceId.localeCompare(b.sourceId) || a.page - b.page);
  return (
    <Workbench
      cards={cards}
      extractions={extractions.filter((e) => cards.some((c) => c.sourceId === e.source_id))}
      sources={sources.filter((s) => cards.some((c) => c.sourceId === s._id))}
      briefs={briefs}
    />
  );
}
