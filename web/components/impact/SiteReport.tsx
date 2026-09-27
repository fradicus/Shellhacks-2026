"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui";
import { dayRisk, replayDate, type DelayInputs } from "./delayModel";
import { money } from "./model";
import { downloadReportPdf } from "./reportPdf";
import { lastYear, type LastYear, type Recent } from "./reportModel";
import type { ForecastDay, SiteHints } from "./siteModel";
import type { HistoryPayload } from "./WeatherDelay";
import s from "./impact.module.css";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAY = 86_400_000;
const parse = (iso: string) => Date.parse(`${iso}T00:00:00Z`);
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);
export const longDate = (d: string | null) => (d ? new Date(parse(d)).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }) : "–");
const today = () => iso(Date.now() - new Date().getTimezoneOffset() * 60_000);

/** Month grid. Each day is tinted by the share of recorded years it crossed a stop rule; the chosen work window is outlined. */
function StartCalendar({ risk, selected, onSelect, window: win, forecast }: { risk: Map<string, number> | null; selected: string | null; onSelect: (d: string) => void; window: { normal: string | null; typical: string | null; worst: string | null }; forecast: Set<string> }) {
  const init = selected ?? today();
  const [cursor, setCursor] = useState({ y: Number(init.slice(0, 4)), m: Number(init.slice(5, 7)) - 1 });
  const first = Date.UTC(cursor.y, cursor.m, 1), lead = new Date(first).getUTCDay();
  const count = new Date(Date.UTC(cursor.y, cursor.m + 1, 0)).getUTCDate();
  const cells = [...Array(lead).fill(null), ...Array.from({ length: count }, (_, i) => iso(first + i * DAY))];
  const move = (k: number) => setCursor(({ y, m }) => ({ y: y + Math.floor((m + k) / 12), m: ((m + k) % 12 + 12) % 12 }));
  const t = today();
  const within = (d: string, end: string | null) => !!selected && !!end && d >= selected && d <= end;
  return <div className={s.calendar}>
    <div className={s.calHead}>
      <button type="button" onClick={() => move(-1)} aria-label="Previous month">‹</button>
      <strong aria-live="polite">{MONTH_NAMES[cursor.m]} {cursor.y}</strong>
      <button type="button" onClick={() => move(1)} aria-label="Next month">›</button>
    </div>
    <div className={s.calGrid} role="grid" aria-label={`Start date, ${MONTH_NAMES[cursor.m]} ${cursor.y}`}>
      {WEEKDAYS.map((w, i) => <span key={i} className={s.calDow} aria-hidden>{w}</span>)}
      {cells.map((d, i) => {
        if (!d) return <span key={`x${i}`} />;
        const r = risk?.get(d.slice(5)) ?? null;
        const state = d === selected ? "start" : within(d, win.normal) ? "normal" : within(d, win.typical) ? "typical" : within(d, win.worst) ? "worst" : undefined;
        return <button key={d} type="button" role="gridcell" className={s.calDay} data-state={state} data-today={d === t || undefined} aria-selected={d === selected}
          aria-label={`${longDate(d)}${r === null ? "" : `, stop day in ${Math.round(r * 100)}% of recorded years`}${forecast.has(d) ? ", NWS forecast available" : ""}`}
          style={r === null ? undefined : { ["--risk" as string]: String(Math.min(1, r * 2.2)) }} onClick={() => onSelect(d)}>
          <span>{Number(d.slice(8))}</span>{forecast.has(d) && <i className={s.calDot} aria-hidden />}
        </button>;
      })}
    </div>
    <div className={s.calLegend}>
      <span><i className={s.calSwatchLow} />Rarely a stop</span><span><i className={s.calSwatchHigh} />Often a stop</span>
      <span><i className={s.calSwatchWin} />Normal finish</span><span><i className={s.calSwatchTyp} />+ typical weather</span><span><i className={s.calSwatchWorst} />+ worst year</span>
      <span><i className={s.calDot} />NWS forecast</span>
    </div>
  </div>;
}

/** Daily rain for the same dates last year; stop days in the warn color; other stop reasons as letters under the bar. */
function LastYearChart({ view, rainRule }: { view: LastYear; rainRule: number | null }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 720, H = 220, L = 38, R = 8, T = 14, B = 44;
  const days = view.days, max = Math.max(0.5, rainRule ?? 0, ...days.map((d) => d.prcp ?? 0));
  const top = max <= 1 ? Math.ceil(max * 4) / 4 : Math.ceil(max);
  const y = (v: number) => T + (H - T - B) * (1 - v / top);
  const band = (W - L - R) / days.length, bw = Math.max(2, Math.min(18, band - 2));
  const ticks = [0, top / 2, top];
  const tip = hover === null ? null : days[hover];
  const letter: Record<string, string> = { wind: "W", heat: "H", freeze: "F", snow: "S" };
  return <div className={s.chartWrap}>
    <svg viewBox={`0 0 ${W} ${H}`} className={s.chart} role="img" aria-label={`Daily rainfall from ${view.start}, ${days.length} days, with stop days highlighted.`}>
      {ticks.map((v) => <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} className={v === 0 ? s.axis : s.grid} /><text x={L - 6} y={y(v) + 4} textAnchor="end" className={s.tick}>{v.toFixed(v < 1 && v > 0 ? 2 : 0)}</text></g>)}
      {rainRule !== null && rainRule <= top && <g><line x1={L} x2={W - R} y1={y(rainRule)} y2={y(rainRule)} className={s.threshold} /><text x={W - R} y={y(rainRule) - 4} textAnchor="end" className={s.tick}>rain stop {rainRule} in</text></g>}
      {days.map((d, i) => {
        const cx = L + band * i + band / 2, stop = d.reasons.length > 0 && d.workday, h = d.prcp ?? 0;
        return <g key={d.date} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
          <rect x={L + band * i} y={T} width={band} height={H - T - B} fill="transparent" />
          {d.prcp === null ? <text x={cx} y={y(0) - 3} textAnchor="middle" className={s.tick}>·</text>
            : h > 0 && <rect x={cx - bw / 2} y={y(h)} width={bw} height={Math.max(1, y(0) - y(h))} rx={Math.min(3, bw / 3)} className={stop ? s.barWorst : s.bar} />}
          {d.reasons.filter((r) => r !== "rain").slice(0, 2).map((r, k) => <text key={r} x={cx} y={H - B + 14 + k * 10} textAnchor="middle" className={s.tickStrong}>{letter[r]}</text>)}
          {!d.workday && <rect x={L + band * i} y={H - B + 2} width={band} height={2} className={s.weekend} />}
          {(i === 0 || new Date(parse(d.date)).getUTCDate() === 1 || i % 7 === 0) && <text x={cx} y={H - 6} textAnchor="middle" className={s.tick}>{d.date.slice(5).replace("-", "/")}</text>}
        </g>;
      })}
    </svg>
    {tip && <div className={s.tooltip} style={{ left: `${((L + band * (hover! + 0.5)) / W) * 100}%` }} role="status">
      <strong>{longDate(tip.date)}{tip.workday ? "" : " · weekend"}</strong>
      <span>Rain {tip.prcp ?? "–"} in · high {tip.tmax ?? "–"}°F · low {tip.tmin ?? "–"}°F</span>
      <span>Wind gust {tip.wind ?? "–"} mph · snow {tip.snow ?? "–"} in</span>
      <span>{tip.reasons.length ? `Stop: ${tip.reasons.join(", ")}${tip.workday ? "" : " (weekend, no work lost)"}` : "Workable"}</span>
    </div>}
  </div>;
}

export type ReportProps = {
  history: HistoryPayload | null; recent: Recent | null; recentError: string | null; loading: boolean;
  pointLabel: string | null; point: { lat: number; lon: number } | null; hints: SiteHints | null; forecast: ForecastDay[];
  inputs: DelayInputs; setInputs: (i: DelayInputs) => void; dayCost: string; setDayCost: (v: string) => void; standbyPerDay: string;
};

export function SiteReport(p: ReportProps) {
  const { history, inputs, setInputs } = p;
  const [start, setStart] = useState<string | null>(null);
  const series = useMemo(() => (history ? { start: history.window.start, prcp_in: history.prcp_in, tmax_f: history.tmax_f, wsf2_mph: history.wsf2_mph, tmin_f: history.tmin_f ?? null, snow_in: history.snow_in ?? null } : null), [history]);
  const risk = useMemo(() => (series ? dayRisk(series, inputs) : null), [series, inputs]);
  const result = useMemo(() => (series && start ? replayDate(series, start, inputs) : null), [series, start, inputs]);
  const report = result?.report ?? null, errors = result?.errors ?? {};
  const span = report?.baselineDays ? Math.min(90, report.baselineDays + Math.ceil(report.worst?.extraDays ?? 0) + 3) : 28;
  const ly = useMemo(() => (series && start ? lastYear(series, p.recent, start, inputs, span) : null), [series, p.recent, start, inputs, span]);
  const rate = (v: string) => (/^\d+(\.\d{1,2})?$/.test(v.trim()) && Number(v) <= 1_000_000_000 ? Math.round(Number(v) * 100) : null);
  const cost = rate(p.dayCost) ?? rate(p.standbyPerDay);
  const costLabel = rate(p.dayCost) !== null ? "your delay-day cost" : "your standby rate";
  const forecastSet = useMemo(() => new Set(p.forecast.map((f) => f.date)), [p.forecast]);
  const win = { normal: report?.target.normalFinish ?? null, typical: report?.target.typicalFinish ?? null, worst: report?.target.worstFinish ?? null };
  const inWindow = start && win.worst ? p.forecast.filter((f) => f.date >= start && f.date <= win.worst!) : [];
  const wetSite = !!p.hints && (p.hints.poorlyDrained || p.hints.wetlandMapped === true);
  const field = (key: keyof DelayInputs, label: string, help: string) => <div className={s.field}>
    <label htmlFor={`rpt-${key}`}>{label}</label>
    <input id={`rpt-${key}`} type="text" inputMode="decimal" autoComplete="off" maxLength={8} value={inputs[key] as string} aria-invalid={!!errors[key as keyof typeof errors]} onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })} />
    <small>{help}</small>
    {errors[key as keyof typeof errors] && <span className={s.error}>{errors[key as keyof typeof errors]}</span>}
  </div>;

  function download() {
    if (!history || !report || !start) return;
    downloadReportPdf({ pointLabel: p.pointLabel ?? "Selected point", point: p.point, start, inputs, history, report, lastYear: ly, cost, costLabel, hints: p.hints, forecast: inWindow });
  }

  return <section className={s.section} aria-labelledby="report-heading" id="report">
    <div className={s.sectionHead}>
      <div><span className="eyebrow">02 / Plan the start date</span><h2 id="report-heading">Pick a start date. Get the weather report.</h2></div>
      <div className={`no-print ${s.actions}`}><Button variant="primary" onClick={download} disabled={!report}>Download PDF</Button></div>
    </div>
    {!p.point && <p className={s.muted}>Pick a site first: search above, click the map, or choose a project.</p>}
    {p.point && p.loading && <p className={s.muted} aria-live="polite">Loading 10 years of station records for {p.pointLabel}…</p>}
    {p.point && !p.loading && !history && <p className={s.warning}>No NOAA station with a complete 2016–2025 rain and temperature record within 30 miles of this point, so no estimate is shown. Try a nearby town.</p>}
    {history && <>
      <p className={s.stationLine}>{p.pointLabel} · records from <a href={history.rain.source_url} target="_blank" rel="noreferrer">{history.rain.name}</a> ({history.rain.distance_mi} mi){history.wind ? <>, wind from {history.wind.name} ({history.wind.distance_mi} mi)</> : ", no wind record nearby"}{history.origin === "live" ? " · looked up live from NOAA" : ""}.</p>
      <div className={s.reportGrid}>
        <StartCalendar risk={risk} selected={start} onSelect={setStart} window={win} forecast={forecastSet} />
        <div className={s.reportSide}>
          <div className={s.reportInputs}>
            {field("workdays", "Workable days needed", "Crew days of actual work.")}
            <div className={s.field}>
              <label htmlFor="rpt-cost">Cost of one delay day · USD</label>
              <input id="rpt-cost" type="text" inputMode="decimal" autoComplete="off" maxLength={16} value={p.dayCost} onChange={(e) => p.setDayCost(e.target.value)} placeholder={p.standbyPerDay ? `Standby: ${p.standbyPerDay}` : ""} />
              <small>Crew, equipment and rentals that keep billing.</small>
            </div>
          </div>
          <details className={s.rules}>
            <summary>Stop rules and assumptions</summary>
            <div className={s.reportInputs}>
              {field("rainIn", "Rain stop · in/day", "0.50 = NOAA day threshold. Blank = off.")}
              {field("windMph", "Wind stop · mph", "28 = ANSI A92.20 platform limit.")}
              {field("heatF", "Heat stop · max °F", "Off unless your plan sets one.")}
              {field("freezeF", "Freeze stop · min °F", "e.g. for concrete work. Blank = off.")}
              {field("snowIn", "Snow stop · in/day", "Blank = off.")}
              {field("dryingDays", "Wet-ground days after rain", "Your assumption. 0 = off.")}
            </div>
            <label className={s.toggle}><input type="checkbox" checked={inputs.weekdaysOnly} onChange={(e) => setInputs({ ...inputs, weekdaysOnly: e.target.checked })} />Weekdays only</label>
          </details>
          {wetSite && inputs.dryingDays.trim() === "0" && <div className={s.suggest} role="note">
            <span>{p.hints!.poorlyDrained ? `Soil survey: ${p.hints!.drainage}` : "NWI wetland mapped"}. Ground can stay too wet to work after rain.</span>
            <button type="button" onClick={() => setInputs({ ...inputs, dryingDays: "1" })}>Try 1 wet-ground day</button>
          </div>}
          {!start && <p className={s.calPrompt}>Tap a day on the calendar to start. Darker days were stop days in more of the last 10 years.</p>}
          {report && start && <div className={s.reportCards} aria-live="polite">
            <div><span className="eyebrow">Normal finish</span><strong>{longDate(report.target.normalFinish)}</strong><span>{report.baselineDays} calendar days, no weather</span></div>
            <div><span className="eyebrow">Typical weather · median of {report.runs.length} years</span><strong>{longDate(report.target.typicalFinish)}</strong><span>+{report.medianExtra} days{cost !== null && report.medianExtra !== null ? ` · ${money(Math.round(report.medianExtra * cost))}` : ""}</span></div>
            <div data-wet="true"><span className="eyebrow">Worst recorded · {report.worst?.year ?? "–"}</span><strong>{longDate(report.target.worstFinish)}</strong><span>+{report.worst?.extraDays ?? "–"} days{cost !== null && report.worst ? ` · ${money(report.worst.extraDays * cost)}` : ""}</span></div>
            <div data-last="true"><span className="eyebrow">This time last year · {ly?.year ?? "–"}</span><strong>{ly?.run ? `+${ly.run.extraDays} days` : "Not available"}</strong><span>{ly?.run ? `${ly.run.stops.rain} rain, ${ly.run.stops.wind} wind, ${ly.run.stops.heat + ly.run.stops.freeze + ly.run.stops.snow} temp/snow stops${ly.run.stops.wet ? `, ${ly.run.stops.wet} wet-ground` : ""}${cost !== null ? ` · ${money(ly.run.extraDays * cost)}` : ""}` : ly ? "Task runs past the latest NOAA record" : p.recentError ?? "No record for last year's dates"}</span></div>
          </div>}
          {cost === null && report && <p className={s.muted}>Add a delay-day cost to put dollars on each scenario.</p>}
        </div>
      </div>
      {report && start && <>
        {inWindow.length > 0 && <div className={s.forecast}>
          <span className="eyebrow">NWS forecast for your first days · weather API</span>
          <ul>{inWindow.map((f) => <li key={f.date}><strong>{longDate(f.date).replace(/, \d{4}$/, "")}</strong><span>{f.summary}</span><em>{f.maxPrecipChance === null ? "–" : `${f.maxPrecipChance}%`} rain chance · {f.maxTemp ?? "–"}°</em></li>)}</ul>
          <small>Chance of precipitation from the National Weather Service. Shown for context; the estimate above uses recorded history.</small>
        </div>}
        <div className={s.lastYearHead}>
          <span className="eyebrow">How it was this time last year</span>
          <h3>{ly ? `${longDate(ly.start)} onward, ${ly.from === "recent" ? "latest NOAA observations" : "10-year record"}` : "Last year's record is not available for these dates"}</h3>
        </div>
        {ly && ly.days.length > 0 && <>
          <LastYearChart view={ly} rainRule={(() => { const v = inputs.rainIn.trim(); return v ? Number(v) : null; })()} />
          <p className={s.muted}>Bars: daily rain (in). Orange: workdays lost to a stop rule. Letters: W wind, H heat, F freeze, S snow. Thin marks: weekends. Dots: no reading.</p>
        </>}
        <details className={s.tableView}><summary>Year-by-year replay for {longDate(start).replace(/^\w+, /, "").replace(/, \d{4}$/, "")}</summary>
          <table className={s.yearTable}><thead><tr><th>Start</th><th>Finished</th><th>Extra days</th><th>Rain</th><th>Wind</th><th>Heat</th><th>Freeze</th><th>Snow</th><th>Wet-ground</th></tr></thead>
            <tbody>{report.runs.map((r) => <tr key={r.year}><td>{r.start}</td><td>{r.finish}</td><td>+{r.extraDays}</td><td>{r.stops.rain}</td><td>{r.stops.wind}</td><td>{r.stops.heat}</td><td>{r.stops.freeze}</td><td>{r.stops.snow}</td><td>{r.stops.wet}</td></tr>)}</tbody></table>
          {report.excluded.length > 0 && <p className={s.muted}>Not replayed: {report.excluded.join(", ")} (ran past the end of the record).</p>}
        </details>
      </>}
    </>}
  </section>;
}
