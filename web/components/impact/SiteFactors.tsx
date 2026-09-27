"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { money } from "./model";
import type { SitePoint } from "./SiteEvidence";
import { SiteMap, type MapProject } from "./SiteMap";
import { evidenceLines, PH_DEPTH_CM, SiteSchema, soilPhSummary, WaterSchema, type SiteEvidenceData, type WaterEvidence } from "./siteModel";
import { calculateShare, calculateTask, emptyShare, emptyTask, type ShareInputs, type TaskInputs } from "./taskModel";
import s from "./impact.module.css";


const TASK_FIELDS: { key: keyof TaskInputs; label: string; help: string; mode: "decimal" | "text" }[] = [
  { key: "productiveHours", label: "Productive hours the task needs", help: "Hours of actual work, excluding waiting for the window.", mode: "decimal" },
  { key: "paidHoursPerDay", label: "Paid hours per shift day", help: "Hours crew and equipment are billed on a day they mobilize.", mode: "decimal" },
  { key: "laborRate", label: "Crew rate · USD / hour", help: "Fully loaded crew rate from your estimate or quote.", mode: "decimal" },
  { key: "equipRate", label: "Equipment rate · USD / hour", help: "Equipment billed for the shift, including idle time.", mode: "decimal" },
  { key: "siteMultiplier", label: "Site condition multiplier", help: "From 1.00. Enter your own factor for matting, access or wet-ground productivity. No default is applied.", mode: "decimal" },
  { key: "siteBasis", label: "Basis for the multiplier", help: "Where the factor comes from: quote, estimator, past job. Required.", mode: "text" },
  { key: "permitCost", label: "Permit and compliance cost · USD", help: "Fixed environmental compliance cost for this task. Enter 0 if none.", mode: "decimal" },
  { key: "standbyPerDay", label: "Standby cost per closed day · USD", help: "Cost of a mobilized day with no usable window. Enter 0 if demobilized.", mode: "decimal" },
];

type Loaded = { loading: boolean; siteError: string | null; waterError: string | null; site: SiteEvidenceData | null; water: WaterEvidence | null };
const IDLE: Loaded = { loading: false, siteError: null, waterError: null, site: null, water: null };

async function getJson<T>(url: string, schema: { parse: (v: unknown) => T }, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok) throw new Error(`Request failed (${response.status}).`);
  return schema.parse(await response.json());
}
const reason = (error: unknown) => error instanceof Error && error.name !== "ZodError" ? error.message : "Response did not match the expected contract.";

/**
 * Fetches in the click handler from our own routes only. Site (soil, weather) and water fail independently, and a
 * newer point aborts the older requests so only the last choice renders.
 */
function useSite() {
  const [point, setPoint] = useState<SitePoint | null>(null);
  const [state, setState] = useState<Loaded>(IDLE);
  const lane = useRef<AbortController | null>(null);
  useEffect(() => () => lane.current?.abort(), []);
  function select(next: SitePoint) {
    lane.current?.abort();
    const controller = new AbortController(); lane.current = controller;
    setPoint(next); setState({ ...IDLE, loading: true });
    const year = Math.max(2017, new Date().getUTCFullYear() - 1);
    const at = { lat: String(next.lat), lon: String(next.lon) };
    Promise.allSettled([
      getJson(`/api/operations/site?${new URLSearchParams({ ...at, year: String(year) })}`, SiteSchema, controller.signal),
      getJson(`/api/operations/water?${new URLSearchParams(at)}`, WaterSchema, controller.signal),
    ]).then(([site, water]) => {
      if (controller.signal.aborted) return;
      setState({
        loading: false,
        site: site.status === "fulfilled" ? site.value : null, siteError: site.status === "rejected" ? `Soil and weather: ${reason(site.reason)}` : null,
        water: water.status === "fulfilled" ? water.value.water : null, waterError: water.status === "rejected" ? `Water: ${reason(water.reason)}` : null,
      });
    });
  }
  return { point, select, ...state };
}

const when = (iso: string) => { const d = new Date(iso); return Number.isFinite(d.getTime()) ? d.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : iso; };

function WaterCard({ water }: { water: WaterEvidence }) {
  const d = water.data;
  const zone = d?.flood?.zones[0];
  const wet = d?.wetlands;
  return <article className={s.factorCard} data-testid="site-water">
    <span className="eyebrow">Water & flood screening · {water.status.replaceAll("_", " ")}</span>
    {!d ? <p className={s.muted}>{water.limitations.at(-1) ?? "Water evidence is unavailable."}</p> : <>
      <div><strong>Flood zone (FEMA NFHL)</strong><p>{!d.flood ? "Unavailable" : zone ? <>Zone {zone.zone ?? "unknown"}{zone.special_flood_hazard_area ? <mark className={s.flag}> Special flood hazard area</mark> : ""}{zone.subtype ? ` · ${zone.subtype}` : ""}</> : "Unknown: no mapped polygon (not Zone X)"}</p></div>
      <div><strong>Wetland (USFWS NWI)</strong><p>{!wet ? "Unavailable" : wet.mapped ? `Mapped · ${wet.features[0]?.wetland_type ?? "type not published"}${wet.features[0]?.attribute ? ` · ${wet.features[0].attribute}` : ""}` : "No NWI polygon at this point"}</p></div>
      <div><strong>Nearest gauges (USGS)</strong>{!d.rivers ? <p>Unavailable</p> : d.rivers.gauges.length ? <ul className={s.evidenceList}>{d.rivers.gauges.slice(0, 3).map((g) => <li key={g.site_id}><span>{g.value === null ? "No reading" : `${g.value} ${g.unit}`} · {g.name}</span><small>{g.distance_mi} mi · {when(g.observed_at)}</small></li>)}</ul> : <p>No active gauge within {d.rivers.search_radius_mi} mi</p>}</div>
      <div><strong>Tides (NOAA)</strong>{!d.tides ? <p>Unavailable</p> : d.tides.station ? <>
        <p className={s.muted}>{d.tides.station.name} · {d.tides.station.distance_mi} mi · ft above MLLW</p>
        <ul className={s.tideList}>{d.tides.highs_lows.map((e) => <li key={e.time} data-type={e.type}><span>{e.type === "high" ? "High" : "Low"}</span><strong>{e.value_ft ?? "–"}</strong><small>{when(e.time)}</small></li>)}</ul>
      </> : <p>No tide station within {d.tides.search_radius_mi} mi</p>}</div>
      <p className={s.muted}>Gauge heights are provisional readings, not flood stages. Flood zone and wetland maps are screening data, not a delineation or permit determination.</p>
    </>}
  </article>;
}

export function SiteFactors({ points, pairLabel, projects }: { points: SitePoint[]; pairLabel: string | null; projects: MapProject[] }) {
  const [manual, setManual] = useState({ lat: "", lon: "" });
  const [manualError, setManualError] = useState<string | null>(null);
  const [task, setTask] = useState<TaskInputs>(emptyTask);
  const [share, setShare] = useState<ShareInputs>(emptyShare);
  const { point, select, loading, siteError, waterError, site, water } = useSite();
  const outcome = calculateTask(task);
  const split = calculateShare(share);
  const evidence = evidenceLines(site, water);
  const ph = soilPhSummary(site?.soil.data ?? null);

  function checkManual() {
    const lat = Number(manual.lat), lon = Number(manual.lon);
    if (!/^-?\d+(\.\d+)?$/.test(manual.lat.trim()) || !/^-?\d+(\.\d+)?$/.test(manual.lon.trim()) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      setManualError("Enter decimal latitude (−90 to 90) and longitude (−180 to 180)."); return;
    }
    setManualError(null);
    select({ label: "Entered point", lat: Math.round(lat * 1e5) / 1e5, lon: Math.round(lon * 1e5) / 1e5 });
  }
  function reset() { setTask(emptyTask()); setShare(emptyShare()); }

  return <>
    <section className={s.section} aria-labelledby="site-heading">
      <span className="eyebrow">02 / Site evidence</span>
      <h2 id="site-heading">What does the ground and water look like?</h2>
      <p className={s.muted}>Click a project or any spot on the map, choose a project center, or enter a point. Flood zone, wetland, gauges, tides, soil and weather are looked up server-side from public sources. They inform your assumptions below; they never set a number.</p>
      <SiteMap projects={projects} point={point} water={water?.data ?? null} onPick={select} />
      <div className={`${s.pointPicker} no-print`}>
        {points.map((p) => <Button key={p.label} variant={point?.label === p.label ? "primary" : undefined} onClick={() => select(p)}>{p.label}</Button>)}
        <label>Latitude<input inputMode="decimal" value={manual.lat} onChange={(e) => setManual({ ...manual, lat: e.target.value })} placeholder="32.33" maxLength={12} /></label>
        <label>Longitude<input inputMode="decimal" value={manual.lon} onChange={(e) => setManual({ ...manual, lon: e.target.value })} placeholder="-81.03" maxLength={12} /></label>
        <Button onClick={checkManual}>Check point</Button>
      </div>
      {!points.length && <p className={s.muted}>{pairLabel ? "Neither project in this pair has a located center, so enter a point." : "No pair attached. Enter a point, or choose a pair above to use its project centers."}</p>}
      {manualError && <p className={s.error} role="alert">{manualError}</p>}
      {point && <p className={s.muted} aria-live="polite">{loading ? `Checking ${point.label} (${point.lat.toFixed(5)}, ${point.lon.toFixed(5)})…` : `${point.label}: ${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}`}</p>}
      {[siteError, waterError].filter(Boolean).map((e) => <p key={e} className={s.warning} role="alert">{e} The worksheet below still works with your own inputs.</p>)}
      {(site || water) && <div className={s.factorGrid}>
        {water && <WaterCard water={water} />}
        <article className={s.factorCard}>
          <span className="eyebrow">Soil pH (survey estimate, {PH_DEPTH_CM.top}–{PH_DEPTH_CM.bottom} cm)</span>
          {!site ? <p className={s.muted}>Soil survey unavailable.</p> : !site.soil.data ? <p className={s.muted}>{site.soil.limitations.at(-1) ?? "Soil survey unavailable."}</p>
            : <><strong className={s.phValue} data-testid="site-ph">{ph.value === null ? "No pH in survey for this map unit" : `pH ${ph.value.toFixed(1)}`}</strong>
              <small className={s.muted}>1:1 soil-water (ph1to1h2o_r) · weighted by component % × horizon thickness · {ph.horizonsUsed} horizons. Estimated from the SSURGO map unit, not a site test.</small></>}
          <span className="eyebrow">Evidence you can cite</span>
          {evidence.length ? <ul className={s.evidenceList}>{evidence.map((line) => <li key={line}><span>{line}</span>
            <button type="button" className="no-print" onClick={() => setTask((t) => ({ ...t, siteBasis: t.siteBasis.includes(line) ? t.siteBasis : [t.siteBasis, line].filter(Boolean).join("; ").slice(0, 400) }))}>Add to basis</button></li>)}</ul>
            : <p className={s.muted}>No citable site facts came back for this point.</p>}
        </article>
      </div>}
    </section>

    <section className={s.section} aria-labelledby="task-heading">
      <div className={s.sectionHead}>
        <div><span className="eyebrow">03 / User scenario</span><h2 id="task-heading">What does a restricted work window cost?</h2></div>
        <div className={`no-print ${s.actions}`}><Button onClick={reset}>Reset site worksheet</Button><Button variant="primary" onClick={() => window.print()}>Print / save PDF</Button></div>
      </div>
      <p className={s.formula}>work days × paid hours/day × (crew + equipment rate) × site multiplier + permit cost + closed days × standby cost</p>
      <p className={s.muted}>Crews are paid for the shift but only work while the window is open. A tighter tide, daylight or flood-stage window adds paid days. Every input starts blank; blank means unknown.</p>
      <div className={s.taskGrid}>
        <div className={s.fields}>
          {TASK_FIELDS.map((field) => {
            const id = `task-${field.key}`;
            return <div className={s.field} key={field.key}>
              <label htmlFor={id}>{field.label}</label>
              <input id={id} type="text" inputMode={field.mode} autoComplete="off" maxLength={field.mode === "text" ? 400 : 24} value={task[field.key]}
                aria-invalid={!!outcome.errors[field.key]} aria-describedby={`${id}-help`} onChange={(e) => setTask({ ...task, [field.key]: e.target.value })} />
              <small id={`${id}-help`}>{field.help}</small>
              {outcome.errors[field.key] && <span className={s.error}>{outcome.errors[field.key]}</span>}
            </div>;
          })}
          <div className={s.field}>
            <label htmlFor="task-windows">Usable hours per calendar day, in order</label>
            <textarea id="task-windows" rows={3} maxLength={3000} value={task.windows} aria-invalid={!!outcome.errors.windows} onChange={(e) => setTask({ ...task, windows: e.target.value })} placeholder="6.5, 5.8, 0, 4.9, 7.2, 8, 8" />
            <small>Hours the site is workable each day after tide, daylight and flood-stage limits. 0 = closed day. Use the tide times above to estimate them.</small>
            {outcome.errors.windows && <span className={s.error}>{outcome.errors.windows}</span>}
          </div>
        </div>
        <div className={s.scenario} data-base="true">
          <div className={s.result} aria-live="polite" aria-atomic="true">
            <span className={s.muted}>Modeled task cost · USD · user scenario</span>
            <strong data-testid="task-total">{outcome.result ? money(outcome.result.total) : "Not calculated"}</strong>
            <span>{outcome.result ? `${outcome.result.workDays} work ${outcome.result.workDays === 1 ? "day" : "days"} + ${outcome.result.deadDays} closed ${outcome.result.deadDays === 1 ? "day" : "days"}` : outcome.shortfallHours !== null ? `The listed days cover the task only partly: ${outcome.shortfallHours} productive hours still unscheduled. Add more days.` : outcome.overflow ? "The amount is too large to calculate safely." : Object.keys(outcome.errors).length ? "Correct the highlighted inputs." : `${outcome.missing} required inputs remaining.`}</span>
          </div>
          {outcome.result && <div className={s.breakdown}><dl>
            <div><dt>Paid crew + equipment</dt><dd>{money(outcome.result.paidCrew)}</dd></div>
            <div><dt>Site multiplier addition</dt><dd>{money(outcome.result.siteExtra)}</dd></div>
            <div><dt>Permit and compliance</dt><dd>{money(outcome.result.permit)}</dd></div>
            <div><dt>Standby on closed days</dt><dd>{money(outcome.result.standby)}</dd></div>
            <div><dt>Paid shift hours not worked</dt><dd>{outcome.result.idleHours.toLocaleString("en-US")} h</dd></div>
            <div><dt>Usable share of paid hours</dt><dd>{(outcome.result.windowFactor * 100).toFixed(1)}%</dd></div>
          </dl><p className={s.muted}>Multiplier basis: {task.siteBasis}</p></div>}
        </div>
      </div>
      <p className={s.disclosure}><strong>Modeled cost, not a bid.</strong> Map screening (FEMA, NWI, SSURGO) is not a wetland delineation, permit determination or geotechnical finding. The multiplier and rates are yours.</p>
    </section>

    <section className={s.section} aria-labelledby="share-heading">
      <span className="eyebrow">04 / Shared access item</span>
      <h2 id="share-heading">If both utilities use one access road, mat run or bridge</h2>
      <p className={s.muted}>Split one shared item pro rata, for example by mat-days or crossings each utility uses. Optionally enter what each would pay to build alone to see the modeled difference.{pairLabel ? ` Pair: ${pairLabel}.` : ""}</p>
      <div className={s.shareGrid}>
        {([["itemCost", "Shared item cost · USD"], ["shareA", "Use share · utility A"], ["shareB", "Use share · utility B"], ["separateA", "A builds alone · USD (optional)"], ["separateB", "B builds alone · USD (optional)"]] as [keyof ShareInputs, string][]).map(([key, label]) =>
          <div className={s.field} key={key}><label htmlFor={`share-${key}`}>{label}</label>
            <input id={`share-${key}`} type="text" inputMode="decimal" autoComplete="off" maxLength={24} value={share[key]} aria-invalid={!!split.errors[key]} onChange={(e) => setShare({ ...share, [key]: e.target.value })} />
            {split.errors[key] && <span className={s.error}>{split.errors[key]}</span>}
          </div>)}
      </div>
      <div className={s.breakdown} aria-live="polite">{split.result ? <dl>
        <div><dt>Utility A pays</dt><dd>{money(split.result.a)}</dd></div>
        <div><dt>Utility B pays</dt><dd>{money(split.result.b)}</dd></div>
        {split.result.differenceA !== null && <div><dt>A: build alone − shared share</dt><dd data-negative={split.result.differenceA < 0}>{money(split.result.differenceA)}</dd></div>}
        {split.result.differenceB !== null && <div><dt>B: build alone − shared share</dt><dd data-negative={split.result.differenceB < 0}>{money(split.result.differenceB)}</dd></div>}
      </dl> : <p className={s.muted}>{Object.keys(split.errors).length ? "Correct the highlighted inputs." : `${split.missing} required inputs remaining.`}</p>}</div>
      <p className={s.muted}>Possible shared activity, not savings. Each utility still files its own permits; a joint pre-application meeting is a question to raise, not an assumption.</p>
    </section>
  </>;
}
