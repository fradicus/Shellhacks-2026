import { replay, rulesFor, validate, type DelayInputs, type Rules, type Series, type YearRun } from "./delayModel";

export type Recent = { start: string; end: string; source_url: string; prcp_in: (number | null)[]; tmax_f: (number | null)[]; tmin_f: (number | null)[]; snow_in: (number | null)[]; wsf2_mph: (number | null)[] | null };
export type DayView = { date: string; prcp: number | null; tmax: number | null; tmin: number | null; snow: number | null; wind: number | null; reasons: string[]; workday: boolean };
export type LastYear = { year: number; from: "recent" | "record"; start: string; days: DayView[]; run: YearRun | null; sourceUrl: string | null };

const DAY = 86_400_000;
const parse = (iso: string) => Date.parse(`${iso}T00:00:00Z`);
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

/** Which rules a single recorded day crossed, e.g. ["rain", "wind"]. Missing readings cross nothing. */
export function reasons(rules: Rules, d: Omit<DayView, "reasons" | "date" | "workday">): string[] {
  const out: string[] = [];
  if (rules.rain !== null && d.prcp !== null && d.prcp >= rules.rain) out.push("rain");
  if (rules.wind !== null && d.wind !== null && d.wind >= rules.wind) out.push("wind");
  if (rules.heat !== null && d.tmax !== null && d.tmax >= rules.heat) out.push("heat");
  if (rules.freeze != null && d.tmin !== null && d.tmin <= rules.freeze) out.push("freeze");
  if (rules.snow != null && d.snow !== null && d.snow >= rules.snow) out.push("snow");
  return out;
}

/**
 * The same dates one year before the chosen start: recent NOAA observations when they cover it, otherwise the 10-year
 * record (for starts more than ~13 months out). Returns null when neither has that year.
 */
export function lastYear(history: Series & { tmin_f?: (number | null)[] | null; snow_in?: (number | null)[] | null }, recent: Recent | null, startIso: string, inputs: DelayInputs, spanDays: number): LastYear | null {
  const v = validate(inputs);
  if (v.workdays === null || !/^\d{4}-\d{2}-\d{2}$/.test(startIso)) return null;
  const year = Number(startIso.slice(0, 4)) - 1;
  let start = `${year}${startIso.slice(4)}`;
  if (!Number.isFinite(parse(start)) || iso(parse(start)) !== start) start = `${year}-02-28`;
  const pick = (s: Series & { tmin_f?: (number | null)[] | null; snow_in?: (number | null)[] | null }, end: string) => (parse(start) >= parse(s.start) && parse(start) <= parse(end) ? s : null);
  const recentSeries = recent ? { start: recent.start, prcp_in: recent.prcp_in, tmax_f: recent.tmax_f, wsf2_mph: recent.wsf2_mph, tmin_f: recent.tmin_f, snow_in: recent.snow_in } : null;
  const historyEnd = iso(parse(history.start) + (history.prcp_in.length - 1) * DAY);
  const series = (recentSeries && recent && pick(recentSeries, recent.end)) || pick(history, historyEnd);
  if (!series) return null;
  const from = series === recentSeries ? "recent" as const : "record" as const;
  const rules = rulesFor(series, v);
  const index = Math.round((parse(start) - parse(series.start)) / DAY);
  const days: DayView[] = [];
  for (let i = 0; i < spanDays && index + i < series.prcp_in.length; i++) {
    const t = parse(series.start) + (index + i) * DAY, weekday = new Date(t).getUTCDay();
    const d = { prcp: series.prcp_in[index + i], tmax: series.tmax_f[index + i], tmin: series.tmin_f?.[index + i] ?? null, snow: series.snow_in?.[index + i] ?? null, wind: series.wsf2_mph?.[index + i] ?? null };
    days.push({ date: iso(t), ...d, reasons: reasons(rules, d), workday: !inputs.weekdaysOnly || (weekday !== 0 && weekday !== 6) });
  }
  return { year, from, start, days, run: replay(series, index, v.workdays, rules, inputs.weekdaysOnly, year), sourceUrl: from === "recent" ? recent!.source_url : null };
}

export type DayYear = { year: number; date: string; prcp: number | null; tmax: number | null; tmin: number | null; snow: number | null; wind: number | null; reasons: string[] };
export type DayDetails = {
  date: string;
  years: DayYear[];
  /** Share of recorded years this calendar day crossed a stop rule (years with no reading are left out). */
  stopShare: number | null;
  recorded: number;
  avgHigh: number | null; avgLow: number | null; wetYears: number; maxRain: number | null; maxWind: number | null; snowYears: number;
  lastYear: (DayYear & { from: "recent" | "record" }) | null;
};

const mean = (v: number[]) => (v.length ? Math.round(v.reduce((a, b) => a + b, 0) / v.length) : null);

/** Everything the records say about one calendar day at this station: each recorded year, then last year. */
export function dayDetails(history: Series & { tmin_f?: (number | null)[] | null; snow_in?: (number | null)[] | null }, recent: Recent | null, dateIso: string, inputs: DelayInputs): DayDetails | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateIso)) return null;
  const v = validate(inputs);
  const md = dateIso.slice(5), t0 = parse(history.start);
  const firstYear = new Date(t0).getUTCFullYear(), lastRecordYear = new Date(t0 + (history.prcp_in.length - 1) * DAY).getUTCFullYear();
  const pickDay = (s: typeof history, rules: Rules, year: number): DayYear | null => {
    const d = `${year}-${md}`;
    if (!Number.isFinite(parse(d)) || iso(parse(d)) !== d) return null; // Feb 29 only in leap years
    const i = Math.round((parse(d) - parse(s.start)) / DAY);
    if (i < 0 || i >= s.prcp_in.length) return null;
    const x = { prcp: s.prcp_in[i], tmax: s.tmax_f[i], tmin: s.tmin_f?.[i] ?? null, snow: s.snow_in?.[i] ?? null, wind: s.wsf2_mph?.[i] ?? null };
    return { year, date: d, ...x, reasons: reasons(rules, x) };
  };
  const rules = rulesFor(history, v);
  const years: DayYear[] = [];
  for (let y = firstYear; y <= lastRecordYear; y++) { const d = pickDay(history, rules, y); if (d) years.push(d); }
  const known = years.filter((y) => y.prcp !== null || y.tmax !== null);
  const nums = (k: "tmax" | "tmin" | "prcp" | "wind") => known.map((y) => y[k]).filter((n): n is number => n !== null);
  // Last year: the latest observations when they include it, otherwise the 10-year record.
  const target = Number(dateIso.slice(0, 4)) - 1;
  let lastYear: DayDetails["lastYear"] = null;
  if (recent) {
    const rs = { start: recent.start, prcp_in: recent.prcp_in, tmax_f: recent.tmax_f, wsf2_mph: recent.wsf2_mph, tmin_f: recent.tmin_f, snow_in: recent.snow_in };
    const d = pickDay(rs, rulesFor(rs, v), target);
    if (d && (d.prcp !== null || d.tmax !== null)) lastYear = { ...d, from: "recent" };
  }
  if (!lastYear) { const d = years.find((y) => y.year === target); if (d) lastYear = { ...d, from: "record" }; }
  return {
    date: dateIso, years, recorded: known.length,
    stopShare: known.length ? known.filter((y) => y.reasons.length).length / known.length : null,
    avgHigh: mean(nums("tmax")), avgLow: mean(nums("tmin")),
    wetYears: known.filter((y) => (y.prcp ?? 0) >= 0.01).length,
    maxRain: nums("prcp").length ? Math.max(...nums("prcp")) : null, maxWind: nums("wind").length ? Math.max(...nums("wind")) : null,
    snowYears: known.filter((y) => (y.snow ?? 0) > 0).length, lastYear,
  };
}
