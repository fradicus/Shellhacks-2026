"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { HazmatSchema, type Point, type ReferenceResponse } from "@/lib/operations/contracts";
import type { VerifiedCoverageResponse, VerifiedListResponse } from "@/lib/verified/types";
import type { PredictionResponse } from "@/lib/outcomes/model";
import {
  ConditionsResponseSchema,
  OutcomeStatusSchema,
  PredictionResponseSchema,
  ReferenceResponseSchema,
  RequestEpoch,
  RouteResponseSchema,
  SiteResponseSchema,
  VerifiedCoverageResponseSchema,
  VerifiedListResponseSchema,
  VisibilityPoller,
  buildOutcomeRequest,
  buildRouteRequest,
  buildSiteRequest,
  conditionsInterval,
  outcomeBinding,
  pointBinding,
  readResponse,
  routeBinding,
  siteBinding,
  type ConditionsResponse,
  type OutcomeDraft,
  type OutcomeStatus,
  type RouteDraft,
  type RouteResponse,
  type SiteDraft,
  type SiteResponse,
} from "./logic";
import { AEFPanel, OutcomePanel, RoadworkPanel, RoutePanel, SoilPanel, StatusBadge, WeatherPanel, formatTime } from "./Evidence";
import styles from "./operations.module.css";

const EMPTY_SITE: SiteDraft = { label: "", lat: "", lon: "", year: "" };
const EMPTY_ROUTE: RouteDraft = {
  originLabel: "", originLat: "", originLon: "", departureLocal: "", heightM: "", widthM: "", lengthM: "",
  grossWeightKg: "", axleCount: "", trailerMode: "", trailers: [], hazmatReviewed: false, hazmat: [],
};
const EMPTY_OUTCOME: OutcomeDraft = { jobType: "", companyId: "", region: "", asOfLocal: "", plannedDurationDays: "", baselineConfirmed: false };

function message(error: unknown) { return error instanceof Error ? error.message : "The request could not be completed."; }
function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className={styles.field}><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
function InlineError({ children }: { children: string | null }) {
  return children ? <p className={styles.formError} role="alert">{children}</p> : null;
}
function Loading({ children }: { children: ReactNode }) { return <span aria-live="polite" className={styles.loading}>{children}</span>; }

export function OperationsDesk() {
  const [reference, setReference] = useState<ReferenceResponse | null>(null);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [coverage, setCoverage] = useState<VerifiedCoverageResponse | null>(null);
  const [coverageError, setCoverageError] = useState<string | null>(null);
  const [outcomeStatus, setOutcomeStatus] = useState<OutcomeStatus | null>(null);
  const [outcomeStatusError, setOutcomeStatusError] = useState<string | null>(null);

  const [siteDraft, setSiteDraft] = useState<SiteDraft>(EMPTY_SITE);
  const [siteResult, setSiteResult] = useState<SiteResponse | null>(null);
  const [activeSite, setActiveSite] = useState<{ label: string; point: Point; year: number } | null>(null);
  const [siteLoading, setSiteLoading] = useState(false);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [siteOutdated, setSiteOutdated] = useState(false);
  const [conditions, setConditions] = useState<ConditionsResponse | null>(null);
  const [conditionsError, setConditionsError] = useState<string | null>(null);
  const [conditionsLoading, setConditionsLoading] = useState(false);

  const [routeDraft, setRouteDraft] = useState<RouteDraft>(EMPTY_ROUTE);
  const [routeResult, setRouteResult] = useState<RouteResponse | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [routeError, setRouteError] = useState<string | null>(null);
  const [routeOutdated, setRouteOutdated] = useState(false);

  const [directoryQuery, setDirectoryQuery] = useState("");
  const [directoryResult, setDirectoryResult] = useState<VerifiedListResponse | null>(null);
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [directoryError, setDirectoryError] = useState<string | null>(null);

  const [outcomeDraft, setOutcomeDraft] = useState<OutcomeDraft>(EMPTY_OUTCOME);
  const [outcomeResult, setOutcomeResult] = useState<PredictionResponse | null>(null);
  const [outcomeLoading, setOutcomeLoading] = useState(false);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);

  const siteLane = useRef(new RequestEpoch());
  const conditionsLane = useRef(new RequestEpoch());
  const routeLane = useRef(new RequestEpoch());
  const directoryLane = useRef(new RequestEpoch());
  const outcomeLane = useRef(new RequestEpoch());

  useEffect(() => {
    const controller = new AbortController();
    void Promise.allSettled([
      fetch("/api/operations/reference", { cache: "no-store", signal: controller.signal }).then((response) => readResponse(response, ReferenceResponseSchema)).then(setReference).catch((error) => { if (!controller.signal.aborted) setReferenceError(message(error)); }),
      fetch("/api/verified/coverage", { cache: "no-store", signal: controller.signal }).then((response) => readResponse(response, VerifiedCoverageResponseSchema)).then(setCoverage).catch((error) => { if (!controller.signal.aborted) setCoverageError(message(error)); }),
      fetch("/api/outcomes/status", { cache: "no-store", signal: controller.signal }).then((response) => readResponse(response, OutcomeStatusSchema)).then(setOutcomeStatus).catch((error) => { if (!controller.signal.aborted) setOutcomeStatusError(message(error)); }),
    ]);
    return () => controller.abort();
  }, []);

  const refreshConditions = useCallback(async (key: string) => {
    const point = JSON.parse(key) as Point;
    const ticket = conditionsLane.current.begin();
    setConditionsLoading(true); setConditionsError(null);
    try {
      const query = new URLSearchParams({ lat: String(point.lat), lon: String(point.lon) });
      const response = await fetch(`/api/operations/conditions?${query}`, { cache: "no-store", signal: ticket.signal });
      const value = await readResponse(response, ConditionsResponseSchema);
      if (!pointBinding(value, point)) throw new Error("Current conditions did not match the active worksite.");
      if (ticket.current()) { setConditions(value); setConditionsError(null); }
    } catch (error) {
      if (ticket.current()) setConditionsError(message(error));
    } finally { if (ticket.current()) setConditionsLoading(false); }
  }, []);

  useEffect(() => {
    if (!activeSite || siteOutdated || !siteResult) return;
    const lane = conditionsLane.current;
    const poller = new VisibilityPoller(conditionsInterval(reference), refreshConditions);
    const key = JSON.stringify(activeSite.point);
    poller.setVisible(document.visibilityState === "visible");
    poller.bind(key);
    const visibility = () => {
      const visible = document.visibilityState === "visible";
      if (!visible) lane.invalidate();
      poller.setVisible(visible);
    };
    document.addEventListener("visibilitychange", visibility);
    return () => { document.removeEventListener("visibilitychange", visibility); poller.stop(); lane.invalidate(); };
  }, [activeSite, reference, refreshConditions, siteOutdated, siteResult]);

  useEffect(() => () => {
    siteLane.current.invalidate(); conditionsLane.current.invalidate(); routeLane.current.invalidate(); directoryLane.current.invalidate(); outcomeLane.current.invalidate();
  }, []);

  const invalidateSiteDraft = (patch: Partial<SiteDraft>) => {
    setSiteDraft((current) => ({ ...current, ...patch }));
    siteLane.current.invalidate(); conditionsLane.current.invalidate(); routeLane.current.invalidate();
    setSiteLoading(false); setConditionsLoading(false); setRouteLoading(false);
    if (siteResult) setSiteOutdated(true);
    if (routeResult) setRouteOutdated(true);
  };

  const changeRoute = (update: (current: RouteDraft) => RouteDraft) => {
    routeLane.current.invalidate(); setRouteLoading(false);
    setRouteDraft(update); if (routeResult) setRouteOutdated(true);
  };

  const changeOutcome = (update: (current: OutcomeDraft) => OutcomeDraft) => {
    outcomeLane.current.invalidate(); setOutcomeLoading(false); setOutcomeResult(null); setOutcomeDraft(update);
  };

  async function checkSite(event: FormEvent) {
    event.preventDefault(); setSiteError(null);
    let built: ReturnType<typeof buildSiteRequest>;
    try { built = buildSiteRequest(siteDraft); } catch (error) { setSiteError(message(error)); return; }
    const ticket = siteLane.current.begin(); setSiteLoading(true);
    try {
      const query = new URLSearchParams({ lat: String(built.request.lat), lon: String(built.request.lon), year: String(built.request.year) });
      const response = await fetch(`/api/operations/site?${query}`, { cache: "no-store", signal: ticket.signal });
      const value = await readResponse(response, SiteResponseSchema);
      if (!siteBinding(value, built.request)) throw new Error("Site evidence did not match the submitted worksite.");
      if (ticket.current()) {
        setSiteResult(value); setActiveSite({ label: built.label, point: { lat: built.request.lat, lon: built.request.lon }, year: built.request.year });
        setConditions({ request: { lat: built.request.lat, lon: built.request.lon }, weather: value.weather, roadwork: value.roadwork });
        setConditionsError(null); setSiteOutdated(false); setRouteOutdated(routeResult !== null);
      }
    } catch (error) { if (ticket.current()) setSiteError(message(error)); }
    finally { if (ticket.current()) setSiteLoading(false); }
  }

  async function checkRoute(event: FormEvent) {
    event.preventDefault(); setRouteError(null);
    if (!activeSite || siteOutdated) { setRouteError("Check the current worksite before requesting a route."); return; }
    let request;
    try { request = buildRouteRequest(routeDraft, activeSite.point); } catch (error) { setRouteError(message(error)); return; }
    const ticket = routeLane.current.begin(); setRouteLoading(true);
    try {
      const response = await fetch("/api/operations/route", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request), signal: ticket.signal });
      const value = await readResponse(response, RouteResponseSchema);
      if (!routeBinding(value, request)) throw new Error("Route evidence did not match the submitted vehicle and trip.");
      if (ticket.current()) { setRouteResult(value); setRouteOutdated(false); }
    } catch (error) { if (ticket.current()) setRouteError(message(error)); }
    finally { if (ticket.current()) setRouteLoading(false); }
  }

  async function searchDirectory(event: FormEvent) {
    event.preventDefault(); setDirectoryError(null);
    const q = directoryQuery.trim();
    if (q.length > 120) { setDirectoryError("Search text must be 120 characters or fewer."); return; }
    const params = new URLSearchParams({ page: "1", limit: "10" });
    if (q) params.set("q", q);
    const ticket = directoryLane.current.begin(); setDirectoryLoading(true);
    try {
      const response = await fetch(`/api/verified?${params}`, { cache: "no-store", signal: ticket.signal });
      const value = await readResponse(response, VerifiedListResponseSchema);
      if (ticket.current()) setDirectoryResult(value);
    } catch (error) { if (ticket.current()) setDirectoryError(message(error)); }
    finally { if (ticket.current()) setDirectoryLoading(false); }
  }

  async function checkOutcome(event: FormEvent) {
    event.preventDefault(); setOutcomeError(null);
    let request;
    try { request = buildOutcomeRequest(outcomeDraft); } catch (error) { setOutcomeError(message(error)); return; }
    const ticket = outcomeLane.current.begin(); setOutcomeLoading(true);
    try {
      const response = await fetch("/api/outcomes/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request), signal: ticket.signal });
      const value = await readResponse(response, PredictionResponseSchema);
      if (value.request !== null && !outcomeBinding(value, request)) throw new Error("Outcome result did not match the submitted cohort.");
      if (ticket.current()) setOutcomeResult(value);
    } catch (error) { if (ticket.current()) setOutcomeError(message(error)); }
    finally { if (ticket.current()) setOutcomeLoading(false); }
  }

  const currentWeather = conditions?.weather ?? siteResult?.weather ?? null;
  const currentRoadwork = conditions?.roadwork ?? siteResult?.roadwork ?? null;
  const routeReady = reference?.providers.find((provider) => provider.id === "route");
  const years = reference?.aef_years ?? [];
  const hazmat = reference?.hazmat ?? [...HazmatSchema.options];
  const conditionRefresh = conditionsInterval(reference) / 1000;
  const sourceSummary = useMemo(() => coverage?.coverage ? `${coverage.coverage.counts.utilities.toLocaleString()} utilities · ${coverage.coverage.data_year} EIA vintage` : null, [coverage]);
  const timeZone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "local device time", []);

  return <main className={styles.page}>
    <header className={styles.hero}>
      <div><p className="eyebrow">Field operations · evidence desk</p><h1>Plan one mobilization</h1><p>Check a confirmed worksite, current conditions, a truck-specific route, and actual-outcome evidence without blending their limits.</p></div>
      <div className={styles.heroRule}><span>01</span><strong>Enter facts</strong><span>02</span><strong>Check sources</strong><span>03</span><strong>Review limits</strong></div>
    </header>

    <section className={styles.readiness} aria-label="Provider readiness">
      <div><span className="eyebrow">Verified directory</span><strong>{coverage?.available ? sourceSummary : coverage?.reason ?? coverageError ?? "Checking…"}</strong></div>
      <div><span className="eyebrow">Current conditions</span><strong>{reference ? `Refresh ${conditionRefresh}s while visible` : referenceError ?? "Checking…"}</strong></div>
      <div><span className="eyebrow">Truck route</span><strong>{routeReady?.ready ? "Configured" : routeReady?.reason ?? "Checking…"}</strong></div>
      <div><span className="eyebrow">Duration model</span><strong>{outcomeStatus?.reason ?? outcomeStatusError ?? "Checking…"}</strong></div>
    </section>

    <div className={styles.workspace}>
      <div className={styles.controls}>
        <section className={styles.panel}>
          <div className={styles.sectionHeading}><span className={styles.step}>01</span><div><h2>Confirm the worksite</h2><p>Coordinates are manual user input. GridBridge does not verify or infer this location.</p></div></div>
          <form onSubmit={checkSite} noValidate>
            <Field label="Worksite label"><input value={siteDraft.label} onChange={(event) => invalidateSiteDraft({ label: event.target.value })} autoComplete="off" required /></Field>
            <div className={styles.fieldGrid}>
              <Field label="Latitude"><input inputMode="decimal" value={siteDraft.lat} onChange={(event) => invalidateSiteDraft({ lat: event.target.value })} placeholder="e.g. 47.6062" required /></Field>
              <Field label="Longitude"><input inputMode="decimal" value={siteDraft.lon} onChange={(event) => invalidateSiteDraft({ lon: event.target.value })} placeholder="e.g. -122.3321" required /></Field>
              <Field label="Annual AEF year" hint="Exact point and year only">
                {years.length ? <select value={siteDraft.year} onChange={(event) => invalidateSiteDraft({ year: event.target.value })} required><option value="">Select year</option>{years.map((year) => <option key={year} value={year}>{year}</option>)}</select>
                  : <input inputMode="numeric" value={siteDraft.year} onChange={(event) => invalidateSiteDraft({ year: event.target.value })} placeholder="YYYY" required />}
              </Field>
            </div>
            <InlineError>{siteError}</InlineError>
            {siteOutdated && <p className={styles.inlineWarning}>Worksite inputs changed. Older evidence remains visible but current-condition polling has stopped.</p>}
            <div className={styles.actions}><button className={styles.primary} disabled={siteLoading}>{siteLoading ? "Checking worksite…" : "Check worksite"}</button>{siteLoading && <Loading>Provider checks are independent; partial results remain possible.</Loading>}</div>
          </form>
        </section>

        <details className={styles.panel}>
          <summary><span className={styles.step}>02</span><span><strong>Reference utility and county evidence</strong><small>Optional · does not set the worksite</small></span></summary>
          <div className={styles.detailBody}>
            <p className={styles.scope}>EIA distribution-equipment counties are reference context, not a transmission project location or exclusive service territory.</p>
            <form onSubmit={searchDirectory} noValidate>
              <Field label="Utility name or EIA ID"><input value={directoryQuery} onChange={(event) => setDirectoryQuery(event.target.value)} /></Field>
              <p className={styles.small}>Use the <a href="/explore">National explorer</a> for named state and county filters.</p>
              <InlineError>{directoryError}</InlineError><button className={styles.secondary} disabled={directoryLoading}>{directoryLoading ? "Searching…" : "Search verified directory"}</button>
            </form>
            {directoryResult && <div className={styles.directoryResults} aria-live="polite">
              <p><strong>{directoryResult.available ? directoryResult.total.toLocaleString() : "Unavailable"}</strong> matching utilities · dataset {directoryResult.dataset ?? "not available"}</p>
              {directoryResult.records.map((record) => <article key={record.id} className={styles.directoryRow}>
                <div><strong>{record.name}</strong><span>EIA {record.eia_utility_id} · {record.data_year}</span></div><StatusBadge status={record.validation_status} />
                <p>States {record.state_fips.join(", ") || "not published"} · counties {record.county_geoids.join(", ") || "not published"}</p>
                <details><summary>Source identity and limits</summary><p className={styles.hash}>{record.source_ids.join(", ")}</p><ul>{record.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>
              </article>)}
              {directoryResult.available && directoryResult.records.length === 0 && <p className={styles.empty}>No match in the imported directory. This does not prove no utility serves the area.</p>}
            </div>}
            {coverage?.coverage && <details className={styles.evidenceDetails}><summary>Directory coverage</summary><p>{coverage.coverage.counts.resolved_county_rows.toLocaleString()} resolved, {coverage.coverage.counts.unresolved_county_rows.toLocaleString()} unresolved, and {coverage.coverage.counts.conflicting_county_rows.toLocaleString()} conflicting territory rows.</p><p>Independently corroborated service claims: {coverage.coverage.counts.independently_corroborated_service_claims}.</p><ul>{coverage.coverage.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>}
          </div>
        </details>

        <details className={styles.panel}>
          <summary><span className={styles.step}>03</span><span><strong>Truck route</strong><small>Optional · explicit vehicle facts required</small></span></summary>
          <form className={styles.detailBody} onSubmit={checkRoute} noValidate>
            <p className={styles.scope}>Destination: {activeSite ? `${activeSite.label} (${activeSite.point.lat}, ${activeSite.point.lon})` : "check a worksite first"}. No route is drawn on the project map.</p>
            <Field label="Origin label"><input value={routeDraft.originLabel} onChange={(event) => changeRoute((value) => ({ ...value, originLabel: event.target.value }))} /></Field>
            <div className={styles.fieldGrid}><Field label="Origin latitude"><input inputMode="decimal" value={routeDraft.originLat} onChange={(event) => changeRoute((value) => ({ ...value, originLat: event.target.value }))} /></Field><Field label="Origin longitude"><input inputMode="decimal" value={routeDraft.originLon} onChange={(event) => changeRoute((value) => ({ ...value, originLon: event.target.value }))} /></Field></div>
            <Field label="Departure" hint={`Local time zone: ${timeZone}`}><input type="datetime-local" value={routeDraft.departureLocal} onChange={(event) => changeRoute((value) => ({ ...value, departureLocal: event.target.value }))} /></Field>
            <div className={styles.fieldGrid}>
              <Field label="Total height (m)" hint="Exact whole millimetres"><input inputMode="decimal" value={routeDraft.heightM} onChange={(event) => changeRoute((value) => ({ ...value, heightM: event.target.value }))} /></Field>
              <Field label="Total width (m)" hint="Exact whole millimetres"><input inputMode="decimal" value={routeDraft.widthM} onChange={(event) => changeRoute((value) => ({ ...value, widthM: event.target.value }))} /></Field>
              <Field label="Total length (m)" hint="Includes trailers"><input inputMode="decimal" value={routeDraft.lengthM} onChange={(event) => changeRoute((value) => ({ ...value, lengthM: event.target.value }))} /></Field>
              <Field label="Gross weight (kg)" hint="Whole kilograms"><input inputMode="numeric" value={routeDraft.grossWeightKg} onChange={(event) => changeRoute((value) => ({ ...value, grossWeightKg: event.target.value }))} /></Field>
              <Field label="Total axles"><input inputMode="numeric" value={routeDraft.axleCount} onChange={(event) => changeRoute((value) => ({ ...value, axleCount: event.target.value }))} /></Field>
            </div>
            <fieldset><legend>Trailer declaration</legend><label className={styles.check}><input type="radio" name="trailer-mode" checked={routeDraft.trailerMode === "none"} onChange={() => changeRoute((value) => ({ ...value, trailerMode: "none", trailers: [] }))} /> No trailers</label><label className={styles.check}><input type="radio" name="trailer-mode" checked={routeDraft.trailerMode === "listed"} onChange={() => changeRoute((value) => ({ ...value, trailerMode: "listed", trailers: value.trailers.length ? value.trailers : [""] }))} /> List trailers</label>
              {routeDraft.trailerMode === "listed" && <div className={styles.trailers}>{routeDraft.trailers.map((trailer, index) => <div key={index}><label>Trailer {index + 1} length (m)<input inputMode="decimal" value={trailer} onChange={(event) => changeRoute((value) => ({ ...value, trailers: value.trailers.map((item, itemIndex) => itemIndex === index ? event.target.value : item) }))} /></label><button type="button" onClick={() => changeRoute((value) => ({ ...value, trailers: value.trailers.filter((_, itemIndex) => itemIndex !== index) }))}>Remove</button></div>)}<button type="button" disabled={routeDraft.trailers.length >= 5} onClick={() => changeRoute((value) => ({ ...value, trailers: [...value.trailers, ""] }))}>Add trailer</button></div>}
            </fieldset>
            <fieldset><legend>Hazardous goods</legend><label className={styles.check}><input type="checkbox" checked={routeDraft.hazmatReviewed} onChange={(event) => changeRoute((value) => ({ ...value, hazmatReviewed: event.target.checked }))} /> I reviewed this list; no selection means none.</label><div className={styles.choiceGrid}>{hazmat.map((item) => <label className={styles.check} key={item}><input type="checkbox" checked={routeDraft.hazmat.includes(item)} onChange={(event) => changeRoute((value) => ({ ...value, hazmat: event.target.checked ? [...value.hazmat, item] : value.hazmat.filter((entry) => entry !== item) }))} /> {item.replaceAll("_", " ").toLowerCase()}</label>)}</div></fieldset>
            <InlineError>{routeError}</InlineError><button className={styles.primary} disabled={routeLoading || !activeSite || siteOutdated}>{routeLoading ? "Checking route…" : "Check truck route"}</button>
          </form>
        </details>

        <details className={styles.panel}>
          <summary><span className={styles.step}>04</span><span><strong>Construction duration evidence</strong><small>Optional · authorized actual histories only</small></span></summary>
          <form className={styles.detailBody} onSubmit={checkOutcome} noValidate>
            <div className={styles.modelStatus}><StatusBadge status={outcomeStatus?.status ?? "unavailable"} /><p>{outcomeStatus?.reason ?? outcomeStatusError ?? "Checking model availability…"}</p></div>
            <div className={styles.fieldGrid}><Field label="Job type"><input value={outcomeDraft.jobType} onChange={(event) => changeOutcome((value) => ({ ...value, jobType: event.target.value }))} /></Field><Field label="Company ID"><input value={outcomeDraft.companyId} onChange={(event) => changeOutcome((value) => ({ ...value, companyId: event.target.value }))} /></Field><Field label="Region"><input value={outcomeDraft.region} onChange={(event) => changeOutcome((value) => ({ ...value, region: event.target.value }))} /></Field></div>
            <Field label="Decision as-of time" hint={`Local time zone: ${timeZone}`}><input type="datetime-local" value={outcomeDraft.asOfLocal} onChange={(event) => changeOutcome((value) => ({ ...value, asOfLocal: event.target.value }))} /></Field>
            <Field label="Planned construction duration (days)" hint="Optional user-provided baseline"><input inputMode="numeric" value={outcomeDraft.plannedDurationDays} onChange={(event) => changeOutcome((value) => ({ ...value, plannedDurationDays: event.target.value, baselineConfirmed: event.target.value ? value.baselineConfirmed : false }))} /></Field>
            {outcomeDraft.plannedDurationDays && <label className={styles.check}><input type="checkbox" checked={outcomeDraft.baselineConfirmed} onChange={(event) => changeOutcome((value) => ({ ...value, baselineConfirmed: event.target.checked }))} /> I confirm this baseline was known at the decision as-of time.</label>}
            <InlineError>{outcomeError}</InlineError><button className={styles.secondary} disabled={outcomeLoading || outcomeStatus?.status !== "ready"}>{outcomeLoading ? "Evaluating…" : "Evaluate actual-outcome cohort"}</button>
          </form>
        </details>
      </div>

      <section className={styles.results} aria-label="Operational evidence">
        <div className={styles.resultsHeading}><div><p className="eyebrow">Evidence board</p><h2>{activeSite?.label ?? "No active worksite"}</h2></div>{conditionsLoading && <Loading>Refreshing current conditions…</Loading>}</div>
        {!siteResult && <div className={styles.blankSlate}><span>+</span><h3>Start with a confirmed point</h3><p>The board keeps weather, road work, annual context, soil, routing, and duration evidence separate.</p></div>}
        {siteResult && <>
          {siteOutdated && <p className={styles.outdated}>Inputs changed · current-condition polling stopped · evidence below retains its original timestamps.</p>}
          <div className={styles.evidenceGrid}>
            {currentWeather && <WeatherPanel envelope={currentWeather} refreshFailed={conditionsError} />}
            {currentRoadwork && <RoadworkPanel envelope={currentRoadwork} refreshFailed={conditionsError} />}
            <SoilPanel envelope={siteResult.soil} />
            <AEFPanel envelope={siteResult.aef} />
          </div>
          {!siteOutdated && activeSite && <div className={styles.refreshLine}><span>Current conditions are bound to {activeSite.point.lat}, {activeSite.point.lon}.</span><button type="button" disabled={conditionsLoading} onClick={() => void refreshConditions(JSON.stringify(activeSite.point))}>Refresh now</button></div>}
        </>}
        {routeResult && <section className={styles.resultGroup}><h2>Route assessment</h2><RoutePanel envelope={routeResult.route} limitations={routeResult.limitations} outdated={routeOutdated} /><details className={styles.routeSamples}><summary>Sampled route context</summary><div className={styles.evidenceGrid}><WeatherPanel envelope={routeResult.weather} /><RoadworkPanel envelope={routeResult.roadwork} /><AEFPanel envelope={routeResult.aef} /></div></details></section>}
        {outcomeResult && <section className={styles.resultGroup}><h2>Outcome evidence</h2><OutcomePanel response={outcomeResult} /></section>}
      </section>
    </div>
    <footer className={styles.footer}><p>Planning evidence only. Unknown or partial provider coverage is not an all-clear, route approval, geotechnical opinion, or construction guarantee.</p><p>Site evidence checked {siteResult ? formatTime(siteResult.weather.retrieved_at) : "not yet"}.</p></footer>
  </main>;
}
