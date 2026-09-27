"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useMemo, useState, useTransition } from "react";
import { Badge, Button, EmptyState, ErrorState } from "@/components/ui";
import {
  applyFilterAction,
  parseNationalFilters,
  serializeNationalFilters,
  STATUS_LABEL,
  validateGeographyFilters,
} from "@/lib/national/filters";
import type {
  GeoBounds,
  NationalActionResult,
  NationalAssistantRenderer,
  NationalExplorerController,
  NationalExplorerPayload,
  NationalFilterAction,
  NationalFilters,
  NationalProject,
  NationalSource,
} from "@/lib/national/types";
import { NationalMap } from "./NationalMap";
import { LocationEvidence } from "./LocationEvidence";
import s from "./national.module.css";

const n = (value: number) => value.toLocaleString("en-US");
const display = (value: string | null | undefined) => value || "Not reported";
type Focus = { kind: "region" | "state" | "county"; code: string } | null;
type HistoryItem =
  | { kind: "filters"; value: NationalFilters }
  | { kind: "selection"; value: string | null }
  | { kind: "focus"; value: Focus };

function evidenceLabel(project: NationalProject): string {
  const parts = [project.evidence.page ? `page ${project.evidence.page}` : null, project.evidence.sheet ? `sheet ${project.evidence.sheet}` : null, project.evidence.row ? `row ${project.evidence.row}` : null];
  return parts.filter(Boolean).join(" · ") || "source row not specified";
}

function rawValue(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (!text) return "Not reported";
  return text.length > 320 ? `${text.slice(0, 317)}…` : text;
}

function SourceEvidence({ project, source }: { project: NationalProject; source?: NationalSource }) {
  const raw = Object.entries(project.evidence.raw).slice(0, 16);
  return (
    <div className={s.evidence}>
      <p><strong>{source?.publisher ?? project.source_id}</strong> · {source?.authority.replaceAll("_", " ") ?? "authority not reported"}</p>
      <p>Vintage: {source?.vintage ?? "not reported"} · Published: {source?.publication_date ?? "not reported"} · Retrieved: {source?.retrieved_at ?? "not reported"}</p>
      <p>{evidenceLabel(project)} · geography: {display(project.geography_basis)} · location review: {project.location_review.replaceAll("_", " ")}</p>
      <p>In service: {display(project.in_service.raw)} <span>({project.in_service.precision})</span></p>
      <p>Access: {source?.access_policy?.replaceAll("_", " ") ?? "not reported"} · SHA-256: <code>{source?.sha256 ?? "not available"}</code></p>
      {source?.notes.length ? <ul>{source.notes.map((note, index) => <li key={`${source._id}-note-${index}`}>{note}</li>)}</ul> : null}
      {source?.landing_url ? <p><a href={source.landing_url} target="_blank" rel="noreferrer">Open source landing page</a></p> : null}
      {project.location_verification ? <LocationEvidence verification={project.location_verification} /> : null}
      {raw.length ? <details><summary>Imported source fields</summary><dl className={s.rawFields}>{raw.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{rawValue(value)}</dd></div>)}</dl></details> : null}
    </div>
  );
}

export function NationalExplorer({
  initial,
  renderAssistant,
  basePath = "/explore",
}: {
  initial: NationalExplorerPayload;
  renderAssistant?: NationalAssistantRenderer;
  basePath?: string;
}) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusedGeography, setFocusedGeography] = useState<Focus>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const geography = initial.geography;
  const currentIds = useMemo(() => [...new Set([...initial.projects, ...initial.mapProjects].map((project) => project._id))], [initial.mapProjects, initial.projects]);
  const currentIdSet = useMemo(() => new Set(currentIds), [currentIds]);
  const sourceById = useMemo(() => new Map(initial.sources.map((source) => [source._id, source])), [initial.sources]);
  const stateById = useMemo(() => new Map(geography?.states.map((state) => [state.state_fips, state.name]) ?? []), [geography]);
  const countyById = useMemo(() => new Map(geography?.counties.map((county) => [county.county_geoid, `${county.full_name}, ${county.state_usps}`]) ?? []), [geography]);
  const selected = useMemo(() => [...initial.projects, ...initial.mapProjects].find((project) => project._id === selectedId) ?? null, [initial.mapProjects, initial.projects, selectedId]);

  const navigate = useCallback((next: NationalFilters, remember = true): NationalActionResult => {
    const issue = validateGeographyFilters(next, geography);
    if (issue) return { ok: false, reason: issue };
    if (next.owner && !initial.facets.owners.includes(next.owner)) return { ok: false, reason: "owner is not in the active dataset" };
    if (next.planningRegion && !initial.facets.planningRegions.includes(next.planningRegion)) return { ok: false, reason: "planning region is not in the active dataset" };
    if (remember) setHistory((items) => [...items, { kind: "filters", value: initial.filters }]);
    const query = serializeNationalFilters(next);
    startTransition(() => router.push(query ? `${basePath}?${query}` : basePath));
    return { ok: true };
  }, [basePath, geography, initial.facets.owners, initial.facets.planningRegions, initial.filters, router]);

  const applyAction = useCallback((action: NationalFilterAction): NationalActionResult => {
    if (action.type === "project.select") {
      if (action.projectId !== null && !currentIdSet.has(action.projectId)) return { ok: false, reason: "project is not in the current loaded results" };
      setHistory((items) => [...items, { kind: "selection", value: selectedId }]);
      setSelectedId(action.projectId);
      return { ok: true };
    }
    if (action.type === "geography.focus" && geography) {
      const exists = action.kind === "region"
        ? geography.regions.some((item) => item.region_code === action.code)
        : action.kind === "state"
          ? geography.states.some((item) => item.state_fips === action.code)
          : geography.counties.some((item) => item.county_geoid === action.code);
      if (!exists) return { ok: false, reason: `unknown ${action.kind} code` };
      setHistory((items) => [...items, { kind: "focus", value: focusedGeography }]);
      setFocusedGeography({ kind: action.kind, code: action.code });
      return { ok: true };
    }
    const next = applyFilterAction(initial.filters, action);
    if (!next) return { ok: false, reason: "unsupported action for this explorer" };
    try {
      const parsed = parseNationalFilters(Object.fromEntries(new URLSearchParams(serializeNationalFilters(next))));
      return navigate(parsed);
    } catch (error) {
      return { ok: false, reason: error instanceof Error ? error.message : "invalid filters" };
    }
  }, [currentIdSet, focusedGeography, geography, initial.filters, navigate, selectedId]);

  const reset = useCallback(() => {
    setSelectedId(null);
    setFocusedGeography(null);
    setValidationError(null);
    applyAction({ type: "filters.reset" });
  }, [applyAction]);
  const undo = useCallback((): NationalActionResult => {
    const previous = history.at(-1);
    if (!previous) return { ok: false, reason: "nothing to undo" };
    setHistory((items) => items.slice(0, -1));
    if (previous.kind === "filters") return navigate(previous.value, false);
    if (previous.kind === "selection") setSelectedId(previous.value);
    else setFocusedGeography(previous.value);
    return { ok: true };
  }, [history, navigate]);

  const controller: NationalExplorerController = useMemo(() => ({
    filters: initial.filters,
    results: { ids: currentIds, total: initial.total, located: initial.locatedTotal, unlocated: initial.unlocatedTotal },
    availability: { loading: pending, available: initial.available, mode: initial.mode },
    reference: {
      regions: geography?.regions ?? [], states: geography?.states ?? [], counties: geography?.counties ?? [], sources: initial.sources,
    },
    selectedProjectId: selectedId,
    applyAction,
    reset,
    undo,
  }), [applyAction, currentIds, geography, initial.available, initial.filters, initial.locatedTotal, initial.mode, initial.sources, initial.total, initial.unlocatedTotal, pending, reset, selectedId, undo]);

  const states = useMemo(() => geography?.states.filter((state) => !initial.filters.region || state.census_region_code === initial.filters.region) ?? [], [geography, initial.filters.region]);
  const counties = useMemo(() => geography?.counties.filter((county) => !initial.filters.state || county.state_fips === initial.filters.state) ?? [], [geography, initial.filters.state]);
  const focusBounds: GeoBounds | null = useMemo(() => {
    if (!geography) return null;
    if (focusedGeography?.kind === "county") return geography.counties.find((item) => item.county_geoid === focusedGeography.code)?.bounds ?? null;
    if (focusedGeography?.kind === "state") return geography.states.find((item) => item.state_fips === focusedGeography.code)?.bounds ?? null;
    if (focusedGeography?.kind === "region") return geography.regions.find((item) => item.region_code === focusedGeography.code)?.bounds ?? null;
    if (initial.filters.county) return geography.counties.find((item) => item.county_geoid === initial.filters.county)?.bounds ?? null;
    if (initial.filters.state) return geography.states.find((item) => item.state_fips === initial.filters.state)?.bounds ?? null;
    if (initial.filters.region) return geography.regions.find((item) => item.region_code === initial.filters.region)?.bounds ?? null;
    return null;
  }, [focusedGeography, geography, initial.filters.county, initial.filters.region, initial.filters.state]);

  const patch = (filters: Partial<Omit<NationalFilters, "page" | "limit">>) => {
    const result = applyAction({ type: "filters.patch", filters });
    setValidationError(result.ok ? null : result.reason ?? "Invalid filter selection");
    return result;
  };
  const submitText = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    patch({ text: String(data.get("text") ?? "").trim() || undefined });
  };
  const pages = Math.max(1, Math.ceil(initial.total / initial.limit));
  const exportQuery = serializeNationalFilters({ ...initial.filters, page: 1 });
  const unknownStateCount = initial.coverage?.sources.reduce((sum, source) => sum + source.unknown_state_count, 0);
  const unknownCountyCount = initial.coverage?.sources.reduce((sum, source) => sum + source.unknown_county_count, 0);

  return (
    <main className={s.page} aria-busy={pending}>
      <header className={s.hero}>
        <div>
          <p className={s.eyebrow}>Evidence-led national discovery</p>
          <h1>Transmission project explorer</h1>
          <p className={s.lede}>Filter the project records actually imported from reviewed sources. Census geography frames the search; it does not create project locations.</p>
        </div>
        <div className={s.modeCard}>
          <span>Data mode</span>
          <strong>{initial.mode === "atlas" ? "Active Atlas dataset" : initial.mode === "snapshot" ? "Local / CI snapshot" : "Projects unavailable"}</strong>
          <small>{initial.dataset ?? "No active national dataset"}</small>
        </div>
      </header>

      {initial.mode === "snapshot" ? <p className={s.banner} role="status">Snapshot mode is explicitly enabled for local or CI review. Production never falls back to these committed project files.</p> : null}
      {!initial.available ? (
        <ErrorState title="National projects unavailable">
          {initial.reason ?? "No active national dataset is available."} {initial.referenceAvailable ? "Government geography and the reviewed source catalog remain available below." : ""}
        </ErrorState>
      ) : null}
      {validationError ? <p className={s.validation} role="alert">{validationError}</p> : null}

      <section className={s.metrics} aria-label="Filtered project counts">
        <div><strong>{initial.available ? n(initial.total) : "—"}</strong><span>filtered records</span></div>
        <div><strong>{initial.available ? n(initial.locatedTotal) : "—"}</strong><span>evidenced points</span></div>
        <div><strong>{initial.available ? n(initial.unlocatedTotal) : "—"}</strong><span>location unknown</span></div>
        <div><strong>{n(initial.sources.filter((source) => source.import_status === "imported").length)}</strong><span>imported sources</span></div>
      </section>

      <section className={s.filters} aria-label="Project filters">
        <div className={s.filterHead}><h2>Refine the imported records</h2><Button onClick={reset}>Reset</Button></div>
        <label>Census region<select value={initial.filters.region ?? ""} onChange={(event) => patch({ region: event.target.value || undefined })}><option value="">All regions</option>{geography?.regions.map((region) => <option key={region.region_code} value={region.region_code}>{region.name}</option>)}</select></label>
        <label>State or territory<select value={initial.filters.state ?? ""} onChange={(event) => patch({ state: event.target.value || undefined })}><option value="">All states</option><optgroup label="States and DC">{states.filter((state) => state.scope !== "territory").map((state) => <option key={state.state_fips} value={state.state_fips}>{state.name}</option>)}</optgroup><optgroup label="Territories (outside Census regions)">{states.filter((state) => state.scope === "territory").map((state) => <option key={state.state_fips} value={state.state_fips}>{state.name}</option>)}</optgroup></select></label>
        <label>County or equivalent<select disabled={!initial.filters.state} value={initial.filters.county ?? ""} onChange={(event) => patch({ county: event.target.value || undefined })}><option value="">{initial.filters.state ? "All counties" : "Choose a state first"}</option>{counties.map((county) => <option key={county.county_geoid} value={county.county_geoid}>{county.full_name}</option>)}</select></label>
        <label>Planning region<select value={initial.filters.planningRegion ?? ""} onChange={(event) => patch({ planningRegion: event.target.value || undefined })}><option value="">All planning regions</option>{initial.facets.planningRegions.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Owner<select value={initial.filters.owner ?? ""} onChange={(event) => patch({ owner: event.target.value || undefined })}><option value="">All reported owners</option>{initial.facets.owners.map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Status<select value={initial.filters.status ?? ""} onChange={(event) => patch({ status: (event.target.value || undefined) as NationalFilters["status"] })}><option value="">All statuses</option>{initial.facets.statuses.map((value) => <option key={value} value={value}>{STATUS_LABEL[value]}</option>)}</select></label>
        <label>In service from<input type="date" value={initial.filters.from ?? ""} onChange={(event) => patch({ from: event.target.value || undefined })} /></label>
        <label>Through<input type="date" value={initial.filters.to ?? ""} onChange={(event) => patch({ to: event.target.value || undefined })} /></label>
        <form className={s.search} onSubmit={submitText}><label>Project text<input key={initial.filters.text ?? ""} name="text" defaultValue={initial.filters.text ?? ""} maxLength={120} placeholder="Name, ID, owner…" /></label><Button variant="primary" type="submit">Search</Button></form>
        {unknownStateCount !== undefined || unknownCountyCount !== undefined ? <p className={s.coverageHint}>Assignment coverage in the published snapshot: {unknownStateCount === undefined ? "unknown" : n(unknownStateCount)} records have no asserted state and {unknownCountyCount === undefined ? "unknown" : n(unknownCountyCount)} have no asserted county. Reference boundaries do not fill those gaps.</p> : null}
      </section>

      <div className={s.workspace}>
        <div className={s.mapCol}>
          <NationalMap
            projects={initial.mapProjects}
            selectedId={selectedId}
            focusBounds={focusBounds}
            emptyMessage={initial.mapProjects.length ? undefined : !initial.available ? "Project points unavailable. Reference geography is not a project dataset." : initial.total ? `${n(initial.total)} records match, but none has an evidenced project point.` : "No project points match the current filters."}
            onSelect={setSelectedId}
          />
          {initial.mapTruncated ? <p className={s.note}>The map reached its 2,000-point safety limit. Narrow the filters; the table count remains exact.</p> : null}
        </div>
        <section className={s.results} aria-label="Filtered projects">
          <div className={s.resultsHead}>
            <div><h2>Projects</h2><p>{initial.available ? <>Showing {initial.projects.length ? n((initial.page - 1) * initial.limit + 1) : 0}–{n(Math.min(initial.page * initial.limit, initial.total))} of {n(initial.total)}</> : "Results unavailable"}</p></div>
            {initial.available ? <div><a className={s.export} href={`/api/national/export${exportQuery ? `?${exportQuery}` : ""}`}>Export CSV</a><br /><a className={s.export} href={`/api/national/export?${exportQuery ? `${exportQuery}&` : ""}format=json`}>Export JSON evidence</a></div> : null}
          </div>
          {!initial.available ? <EmptyState title="Project records are unavailable">Reference geography is not a project dataset.</EmptyState> : initial.projects.length === 0 ? <EmptyState title="No matches in the imported records">This does not mean the selected area has no planned construction. Records with unknown state or county cannot satisfy a geographic filter.</EmptyState> : (
            <ol className={s.projectList}>
              {initial.projects.map((project) => {
                const source = sourceById.get(project.source_id);
                return <li key={project._id}><button className={project._id === selectedId ? s.selectedRow : s.projectRow} onClick={() => setSelectedId(project._id)}><span><strong>{project.name}</strong><small>{project.native_id} · {display(project.owner)}</small></span><span className={s.rowMeta}><Badge tone={project.center ? "ok" : "warn"}>{project.center ? project.location_review.replaceAll("_", " ") : "location unknown"}</Badge><small>{STATUS_LABEL[project.status_group]}</small></span></button><details><summary>Source evidence</summary><SourceEvidence project={project} source={source} /></details></li>;
              })}
            </ol>
          )}
          <div className={s.pagination}><Button disabled={initial.page <= 1 || pending} onClick={() => navigate({ ...initial.filters, page: initial.page - 1 }, false)}>Previous</Button><span>Page {n(initial.page)} of {n(pages)}</span><Button disabled={initial.page >= pages || pending} onClick={() => navigate({ ...initial.filters, page: initial.page + 1 }, false)}>Next</Button></div>
        </section>
      </div>

      {selected ? <aside className={s.drawer} aria-label="Selected project details"><div><p className={s.eyebrow}>Selected project</p><h2>{selected.name}</h2></div><Button onClick={() => setSelectedId(null)}>Close</Button><dl><div><dt>Owner</dt><dd>{display(selected.owner)}</dd></div><div><dt>Planning region</dt><dd>{display(selected.planning_region)}</dd></div><div><dt>Reported states</dt><dd>{selected.states.map((code) => stateById.get(code) ?? code).join(", ") || "Unknown"}</dd></div><div><dt>Reported counties</dt><dd>{selected.counties.map((code) => countyById.get(code) ?? code).join(", ") || "Unknown"}</dd></div><div><dt>Location basis</dt><dd>{display(selected.geography_basis)}</dd></div><div><dt>Milestone</dt><dd>{display(selected.in_service.raw)} ({selected.in_service.precision})</dd></div></dl><p>{selected.description ?? "No description was published in the imported row."}</p><div className={s.drawerEvidence}><SourceEvidence project={selected} source={sourceById.get(selected.source_id)} /></div></aside> : null}

      <section className={s.provenance}>
        <div><p className={s.eyebrow}>Coverage boundary</p><h2>What this explorer knows</h2><p>{initial.coverage?.projects_total !== undefined ? `${n(initial.coverage.projects_total)} records were imported in the published snapshot.` : "No active project coverage report is available."} Government reference geography covers more places than the imported project sources.</p></div>
        <details><summary>Reviewed source catalog ({n(initial.sources.length)})</summary><ul>{initial.sources.map((source) => <li key={source._id}><strong>{source.title}</strong> — {source.import_status.replaceAll("_", " ")} · {source.authority.replaceAll("_", " ")} · vintage {source.vintage ?? "not reported"} · published {source.publication_date ?? "not reported"} · retrieved {source.retrieved_at ?? "not reported"} · access {source.access_policy?.replaceAll("_", " ") ?? "not reported"} · SHA-256 <code>{source.sha256 ?? "not available"}</code>{source.landing_url ? <> · <Link href={source.landing_url}>source</Link></> : null}{source.notes.length ? <ul>{source.notes.map((note, index) => <li key={`${source._id}-catalog-note-${index}`}>{note}</li>)}</ul> : null}</li>)}</ul></details>
      </section>

      {renderAssistant ? renderAssistant(controller) : null}
    </main>
  );
}
