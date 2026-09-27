"use client";

import { useMemo, useState } from "react";
import { byStartMonth, MONTHS, type DelayInputs, type MonthSummary } from "./delayModel";
import { money } from "./model";
import { phClass, SOIL_SURVEY_MANUAL, type SiteHints } from "./siteModel";
import s from "./impact.module.css";

export type HistoryPayload = {
  origin?: "committed" | "live";
  window: { start: string; end: string };
  citation: string;
  rain: { id: string; name: string; distance_mi: number; source_url: string };
  wind: { id: string; name: string; distance_mi: number; source_url: string } | null;
  prcp_in: (number | null)[];
  tmax_f: (number | null)[];
  tmin_f?: (number | null)[] | null;
  snow_in?: (number | null)[] | null;
  wsf2_mph: (number | null)[] | null;
};

/** USACE FY2024 averages, quoted in the Federal Register notice proposing the 2026 nationwide permits (doc 2025-11190). */
const PERMITS = {
  none: { label: "No Corps permit assumed", days: 0 },
  nwp: { label: "Nationwide Permit with pre-construction notification (FY2024 avg 55 days)", days: 55 },
  ip: { label: "Standard individual permit (FY2024 avg 253 days)", days: 253 },
} as const;
const PERMIT_SOURCE = "https://www.govinfo.gov/content/pkg/FR-2025-06-18/html/2025-11190.htm";

const fmt = (v: number | null, digits = 1) => (v === null ? "–" : Number.isInteger(v) ? String(v) : v.toFixed(digits));
const plural = (n: number, word: string) => `${fmt(n)} ${word}${n === 1 ? "" : "s"}`;

/** Bars = median extra calendar days by start month; whisker = best to worst year. Single series, so no legend box. */
function MonthChart({ months, selected, onSelect }: { months: MonthSummary[]; selected: number; onSelect: (m: number) => void }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 260, L = 36, R = 8, T = 16, B = 30;
  const max = Math.max(1, ...months.map((m) => m.maxExtra ?? 0));
  const step = max <= 5 ? 1 : max <= 12 ? 2 : max <= 30 ? 5 : 10;
  const top = Math.ceil(max / step) * step;
  const y = (v: number) => T + (H - T - B) * (1 - v / top);
  const band = (W - L - R) / 12, bw = Math.min(34, band - 10);
  const top1 = Math.max(...months.map((m) => m.medianExtra ?? -1));
  const tip = hover === null ? null : months[hover];
  return <div className={s.chartWrap}>
    <svg viewBox={`0 0 ${W} ${H}`} className={s.chart} role="img" aria-label="Median extra calendar days by start month, with best-to-worst year range. Table view below.">
      {Array.from({ length: top / step + 1 }, (_, i) => i * step).map((v) => <g key={v}>
        <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className={v === 0 ? s.axis : s.grid} />
        <text x={L - 8} y={y(v) + 4} textAnchor="end" className={s.tick}>{v}</text>
      </g>)}
      {months.map((m, i) => {
        const cx = L + band * i + band / 2;
        const isWorst = m.medianExtra !== null && m.medianExtra === top1, isSel = selected === m.month;
        return <g key={m.month} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onClick={() => onSelect(m.month)} style={{ cursor: "pointer" }}>
          <rect x={L + band * i} y={T} width={band} height={H - T - B} fill="transparent" />
          {m.medianExtra !== null && <>
            <path d={`M${cx - bw / 2},${y(0)} V${y(m.medianExtra) + 4} q0,-4 4,-4 H${cx + bw / 2 - 4} q4,0 4,4 V${y(0)} Z`} className={isWorst ? s.barWorst : s.bar} data-selected={isSel || hover === i} />
            <line x1={cx} x2={cx} y1={y(m.minExtra!)} y2={y(m.maxExtra!)} className={s.whisker} />
            <line x1={cx - 5} x2={cx + 5} y1={y(m.maxExtra!)} y2={y(m.maxExtra!)} className={s.whisker} />
            {isWorst && <text x={cx} y={y(m.maxExtra!) - 6} textAnchor="middle" className={s.tickStrong}>worst</text>}
          </>}
          <text x={cx} y={H - 10} textAnchor="middle" className={isSel ? s.tickStrong : s.tick}>{MONTHS[m.month]}</text>
        </g>;
      })}
    </svg>
    {tip && <div className={s.tooltip} style={{ left: `${((L + band * (hover! + 0.5)) / W) * 100}%` }} role="status">
      <strong>Start {MONTHS[tip.month]} 1</strong>
      <span>Median {fmt(tip.medianExtra)} extra days</span>
      <span>Best {fmt(tip.minExtra)} · worst {fmt(tip.maxExtra)}{tip.worstYear ? ` (${tip.worstYear})` : ""}</span>
      <span>{tip.runs.length} years replayed{tip.excluded.length ? `, ${tip.excluded.length} ran past the record` : ""}</span>
    </div>}
  </div>;
}

export function WeatherDelay({ history, loading, error, standbyPerDay, hints, inputs, dayCost }: { history: HistoryPayload | null; loading: boolean; error: string | null; standbyPerDay: string; hints: SiteHints | null; inputs: DelayInputs; dayCost: string }) {
  const [permit, setPermit] = useState<keyof typeof PERMITS>("none");
  const [month, setMonth] = useState<number>(new Date().getUTCMonth());
  const result = useMemo(() => (history ? byStartMonth({ start: history.window.start, prcp_in: history.prcp_in, tmax_f: history.tmax_f, wsf2_mph: history.wsf2_mph, tmin_f: history.tmin_f ?? null, snow_in: history.snow_in ?? null }, inputs) : null), [history, inputs]);
  const months = result?.months ?? null;
  const sel = months?.[month] ?? null;
  const ranked = months?.filter((m) => m.medianExtra !== null) ?? [];
  // Ties are all named; the worst-year figure comes from the tied month with the largest single-year delay.
  const hi = ranked.length ? Math.max(...ranked.map((m) => m.medianExtra!)) : null, lo = ranked.length ? Math.min(...ranked.map((m) => m.medianExtra!)) : null;
  const worstMonths = ranked.filter((m) => m.medianExtra === hi), bestMonths = ranked.filter((m) => m.medianExtra === lo);
  const worst = worstMonths.reduce<MonthSummary | null>((a, m) => (!a || (m.maxExtra ?? 0) > (a.maxExtra ?? 0) ? m : a), null);
  const best = bestMonths[0] ?? null;
  const names = (list: MonthSummary[]) => list.map((m) => MONTHS[m.month]).join(" / ");
  // Cost of one weather day: this panel's own input, else the worksheet's standby rate. Blank stays unpriced.
  const rate = (v: string) => (/^\d+(\.\d{1,2})?$/.test(v.trim()) && Number(v) <= 1_000_000_000 ? Math.round(Number(v) * 100) : null);
  const standby = rate(dayCost) ?? rate(standbyPerDay);
  const costBasis = rate(dayCost) !== null ? "your delay-day cost" : "your standby rate";

  const years = history ? `${history.window.start.slice(0, 4)}–${history.window.end.slice(0, 4)}` : "the last 10 years";
  return <section className={s.section} aria-labelledby="delay-heading">
    <span className="eyebrow">03 / Why timing matters</span>
    <h2 id="delay-heading">How much longer does weather make this task?</h2>
    <p className={s.muted}>Each start month is replayed against every year of recorded daily weather at the nearest NOAA station ({years}). A day is lost when it crosses a stop rule below; the task finishes when it has banked its workable days. No forecast, no probability model: this is what actually would have happened.</p>
    {loading && <p className={s.muted} aria-live="polite">Loading 10 years of station records…</p>}
    {error && <p className={s.warning} role="alert">{error}</p>}
    {!loading && !error && !history && <p className={s.muted}>Pick a point on the map. Weather history is available within 30 mi of an analyzed NOAA station with a complete 2016–2025 record.</p>}
    {history && <>
      <p className={s.stationLine}>
        Rain and heat: <a href={history.rain.source_url} target="_blank" rel="noreferrer">{history.rain.name}</a> · {history.rain.distance_mi} mi.{" "}
        Wind: {history.wind ? <><a href={history.wind.source_url} target="_blank" rel="noreferrer">{history.wind.name}</a> · {history.wind.distance_mi} mi.</> : "no station with a complete wind record nearby, so the wind rule is off."}{" "}
        <a href={history.citation} target="_blank" rel="noreferrer">NOAA NCEI GHCN-Daily</a>
      </p>
      <p className={s.muted}>Uses the stop rules and delay-day cost from the report above.</p>
      {result?.rulesOff && <p className={s.warning}>Every stop rule is off, so weather adds nothing. Turn on at least one rule.</p>}
      {months && worst && best && <>
        <div className={s.headline} aria-live="polite">
          <div><span className="eyebrow">Worst {worstMonths.length > 1 ? "months" : "month"} to start</span><strong>{names(worstMonths)}</strong><span>median +{plural(worst.medianExtra!, "day")}, up to +{fmt(worst.maxExtra)} ({MONTHS[worst.month]} {worst.worstYear})</span></div>
          <div><span className="eyebrow">Best {bestMonths.length > 1 ? "months" : "month"} to start</span><strong>{names(bestMonths)}</strong><span>median +{plural(best.medianExtra!, "day")}</span></div>
          <div><span className="eyebrow">Timing alone is worth</span><strong>{fmt(worst.medianExtra! - best.medianExtra!)} days</strong><span>{standby !== null ? `${money(Math.round((worst.medianExtra! - best.medianExtra!) * standby))} at ${costBasis}` : "Add a delay-day cost to price it"}</span></div>
        </div>
        {sel && sel.runs.length > 0 && (() => {
          const wetRun = sel.runs.reduce((a, r) => (r.extraDays > a.extraDays ? r : a));
          const base = sel.runs[0].baselineDays, permitDays = PERMITS[permit].days;
          return <div className={s.scenarioCards} aria-live="polite">
            <div><span className="eyebrow">Typical year · start {MONTHS[month]} 1</span><strong>+{plural(sel.medianExtra!, "day")}</strong>
              <span>{base} → {fmt(base + sel.medianExtra!)} calendar days</span><em>{standby !== null ? `${money(Math.round(sel.medianExtra! * standby))} at ${costBasis}` : "Add a delay-day cost to price it"}</em></div>
            <div data-wet="true"><span className="eyebrow">Worst recorded year · {wetRun.year} replayed</span><strong>+{plural(wetRun.extraDays, "day")}</strong>
              <span>{wetRun.stops.rain} rain stops{wetRun.stops.wet ? `, ${wetRun.stops.wet} wet-ground days` : ""}{wetRun.stops.wind ? `, ${wetRun.stops.wind} wind` : ""}{wetRun.stops.heat ? `, ${wetRun.stops.heat} heat` : ""}</span>
              <em>{standby !== null ? `${money(wetRun.extraDays * standby)} at ${costBasis}` : "Add a delay-day cost to price it"}</em></div>
            <div data-permit={hints?.wetlandMapped ? "flag" : undefined}><span className="eyebrow">Wetland permit lead time{hints?.wetlandMapped ? " · wetland mapped here" : ""}</span>
              <select aria-label="Wetland permit assumption" value={permit} onChange={(e) => setPermit(e.target.value as keyof typeof PERMITS)}>{Object.entries(PERMITS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
              <span>Before mobilization: {permitDays ? `+${permitDays} days` : "none"}. Typical total ≈ {fmt(permitDays + base + sel.medianExtra!)} days from application.</span>
              <em><a href={PERMIT_SOURCE} target="_blank" rel="noreferrer">USACE FY2024 averages</a>; not priced, crews are not yet mobilized.</em></div>
          </div>;
        })()}
        <MonthChart months={months} selected={month} onSelect={setMonth} />
        <p className={s.muted}>Bars: median extra calendar days across replayed years. Lines: best to worst year. Click a month for its year-by-year record.</p>
        {sel && <div className={s.monthDetail}>
          <label>Start date<select value={month} onChange={(e) => setMonth(Number(e.target.value))}>{MONTHS.map((m, i) => <option key={m} value={i}>{m} 1</option>)}</select></label>
          {sel.runs.length ? <>
            <p>Normally about <strong>{sel.runs[0].baselineDays} calendar days</strong>. With recorded weather: median <strong>+{fmt(sel.medianExtra)}</strong>, best +{fmt(sel.minExtra)}, worst +{fmt(sel.maxExtra)} ({sel.worstYear}).
              {standby !== null && <> At {costBasis} that is {money(Math.round(sel.medianExtra! * standby))} median and {money(sel.maxExtra! * standby)} in the worst year.</>}</p>
            <table className={s.yearTable}><thead><tr><th>Year</th><th>Calendar days</th><th>Extra</th><th>Rain stops</th><th>Wind stops</th><th>Heat stops</th><th>Wet-ground</th><th>Missing readings</th></tr></thead>
              <tbody>{sel.runs.map((r) => <tr key={r.year}><td>{r.year}</td><td>{r.calendarDays}</td><td>+{r.extraDays}</td><td>{r.stops.rain}</td><td>{r.stops.wind}</td><td>{r.stops.heat}</td><td>{r.stops.wet}</td><td>{r.missing}</td></tr>)}</tbody></table>
            {sel.excluded.length > 0 && <p className={s.muted}>Not replayed: {sel.excluded.join(", ")} (the task would run past the end of the record).</p>}
          </> : <p className={s.muted}>No year could be replayed for this start month.</p>}
        </div>}
        <details className={s.tableView}><summary>Table view: all start months</summary>
          <table className={s.yearTable}><thead><tr><th>Start</th><th>Median extra</th><th>Best</th><th>Worst (year)</th><th>Years</th><th>Share of calendar lost</th></tr></thead>
            <tbody>{months.map((m) => <tr key={m.month}><td>{MONTHS[m.month]} 1</td><td>{fmt(m.medianExtra)}</td><td>{fmt(m.minExtra)}</td><td>{fmt(m.maxExtra)}{m.worstYear ? ` (${m.worstYear})` : ""}</td><td>{m.runs.length}</td><td>{m.lostShare === null ? "–" : `${(m.lostShare * 100).toFixed(1)}%`}</td></tr>)}</tbody></table>
        </details>
      </>}
      {hints && <div className={s.conditions}>
        <span className="eyebrow">How this site&rsquo;s ground adds time</span>
        <dl>
          <div><dt>Wetland</dt><dd>{hints.wetlandMapped === null ? "Wetland map unavailable for this point." : hints.wetlandMapped
            ? <>Mapped in NWI{hints.wetlandType ? ` (${hints.wetlandType})` : ""}. Fill or matting in waters of the U.S. can need a Section 404 permit: the Corps averaged <strong>55 days</strong> for a nationwide-permit notification and <strong>253 days</strong> for an individual permit in FY2024 (<a href={PERMIT_SOURCE} target="_blank" rel="noreferrer">Federal Register</a>). That is lead time before work. In the field, saturated ground is what the wet-ground rule models; we found no published average for matting productivity, so none is applied.</>
            : "No NWI wetland polygon here. Unmapped wetlands can still exist; a delineation decides."}</dd></div>
          <div><dt>Drainage</dt><dd>{hints.drainage ? <>{hints.drainage} (SSURGO). {hints.poorlyDrained ? "Poorly drained soils hold water near the surface after rain; that is why the wet-ground rule is suggested." : "Water drains faster here, so rain stops alone are usually the right model."}</> : "Soil drainage class not available."}</dd></div>
          <div><dt>Soil pH</dt><dd>{hints.ph === null ? "No pH in the soil survey for this map unit." : <>pH {hints.ph.toFixed(1)}, <a href={SOIL_SURVEY_MANUAL} target="_blank" rel="noreferrer">{phClass(hints.ph)?.toLowerCase()}</a>. pH does not add weather days. Acidic soil raises corrosion risk for buried steel and concrete, so it changes foundation materials and coatings (cost and design), not the schedule; NRCS rates this per soil as corrosion of steel and concrete. No delay is added for pH.</>}</dd></div>
          <div><dt>Flood zone</dt><dd>{hints.floodZone ? <>FEMA zone {hints.floodZone}{hints.sfha ? ", a special flood hazard area" : ""}. River and tidal flooding are not in this replay yet; the gauge and tide cards above show current conditions.</> : "FEMA flood zone unknown here."}</dd></div>
        </dl>
      </div>}
      <p className={s.disclosure}><strong>Historical replay, not a forecast.</strong> Station weather can differ from the site; wet ground, river stage and tides can add days these rules do not see. Missing readings are counted as workable and shown per year.</p>
    </>}
  </section>;
}
