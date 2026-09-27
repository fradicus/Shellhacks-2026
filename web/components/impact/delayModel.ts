/**
 * Historical replay: "if this task had started on the 1st of month M in each of the last 10 years, how many extra
 * calendar days would the recorded weather have added?" Each year is replayed day by day from real station records.
 * There is no probability model, no fitted curve and no imputation: a missing reading never stops work, and every
 * such day is counted and shown.
 *
 * baseline days = calendar days to finish N workable days with no weather stops (weekends still skipped if chosen)
 * extra days    = replayed calendar days − baseline days
 */
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const;

export type Series = { start: string; prcp_in: (number | null)[]; tmax_f: (number | null)[]; wsf2_mph: (number | null)[] | null; tmin_f?: (number | null)[] | null; snow_in?: (number | null)[] | null };
export type DelayInputs = { workdays: string; weekdaysOnly: boolean; rainIn: string; windMph: string; heatF: string; dryingDays: string; freezeF: string; snowIn: string };
/**
 * dryingDays is the wet-ground rule: after a rain stop, this many following workdays are also lost while the ground
 * dries. It starts at 0; the UI suggests it (never applies it) when the soil survey says poorly drained or NWI maps a wetland.
 *
 * Visible, editable stop rules. Rain 0.50 in is a standard NOAA climate-normals day-count threshold; wind 28 mph is the
 * 12.5 m/s rated-wind limit for aerial work platforms in ANSI/SAIA A92.20. Heat has no common stop rule, so it starts off.
 */
/** Freeze and snow start off: stop temperatures and snow depths depend on the work (concrete, cranes, access), so the user sets them. */
export const DEFAULT_DELAY: DelayInputs = { workdays: "20", weekdaysOnly: true, rainIn: "0.50", windMph: "28", heatF: "", dryingDays: "0", freezeF: "", snowIn: "" };

export type YearRun = { year: number; calendarDays: number; baselineDays: number; extraDays: number; stops: { rain: number; wind: number; heat: number; wet: number; freeze: number; snow: number }; missing: number };
export type MonthSummary = { month: number; runs: YearRun[]; excluded: number[]; medianExtra: number | null; minExtra: number | null; maxExtra: number | null; worstYear: number | null; lostShare: number | null };

const DAY = 86_400_000;
const parseDay = (iso: string) => Date.parse(`${iso}T00:00:00Z`);

function threshold(value: string, max: number): { value: number | null; error: string | null } {
  const v = value.trim();
  if (!v) return { value: null, error: null }; // blank = this rule is off, shown as off
  if (!/^\d+(\.\d{1,2})?$/.test(v) || Number(v) <= 0 || Number(v) > max) return { value: null, error: `Enter a number above 0 and up to ${max}, or leave blank to turn this rule off.` };
  return { value: Number(v), error: null };
}

export function validate(inputs: DelayInputs) {
  const errors: Partial<Record<keyof DelayInputs, string>> = {};
  const n = inputs.workdays.trim();
  if (!/^\d+$/.test(n) || Number(n) < 1 || Number(n) > 250) errors.workdays = "Enter whole workable days from 1 to 250.";
  const rain = threshold(inputs.rainIn, 20), wind = threshold(inputs.windMph, 150), heat = threshold(inputs.heatF, 130);
  // Freeze is "min temperature at or below"; negative °F is allowed, so it has its own parse.
  const f = inputs.freezeF.trim();
  const freeze = !f ? null : /^-?\d+(\.\d)?$/.test(f) && Number(f) >= -60 && Number(f) <= 60 ? Number(f) : NaN;
  if (Number.isNaN(freeze)) errors.freezeF = "Enter °F from -60 to 60, or leave blank to turn this rule off.";
  const snow = threshold(inputs.snowIn, 60);
  if (snow.error) errors.snowIn = snow.error;
  if (rain.error) errors.rainIn = rain.error;
  if (wind.error) errors.windMph = wind.error;
  if (heat.error) errors.heatF = heat.error;
  const dry = inputs.dryingDays.trim() || "0";
  if (!/^\d+$/.test(dry) || Number(dry) > 10) errors.dryingDays = "Enter whole drying days from 0 to 10.";
  return { errors, workdays: errors.workdays ? null : Number(n), rain: rain.value, wind: wind.value, heat: heat.value, drying: errors.dryingDays ? 0 : Number(dry), freeze: Number.isNaN(freeze) ? null : freeze, snow: snow.value };
}

/** Replays one start date. Returns null when the record ends before the task would have finished. */
export type Rules = { rain: number | null; wind: number | null; heat: number | null; drying?: number; freeze?: number | null; snow?: number | null };
export function replay(series: Series, startIndex: number, workdays: number, rules: Rules, weekdaysOnly: boolean, year: number): YearRun | null {
  const t0 = parseDay(series.start);
  const length = series.prcp_in.length;
  let done = 0, base = 0, baselineDays: number | null = null, missing = 0;
  const stops = { rain: 0, wind: 0, heat: 0, wet: 0, freeze: 0, snow: 0 };
  let drying = 0; // workdays still lost to wet ground after the last rain stop
  for (let i = startIndex; i < length; i++) {
    const weekday = new Date(t0 + i * DAY).getUTCDay();
    if (weekdaysOnly && (weekday === 0 || weekday === 6)) continue;
    if (baselineDays === null && ++base === workdays) baselineDays = i - startIndex + 1;
    const p = series.prcp_in[i], t = series.tmax_f[i], w = series.wsf2_mph?.[i] ?? null, lo = series.tmin_f?.[i] ?? null, sn = series.snow_in?.[i] ?? null;
    const freezeRule = rules.freeze ?? null, snowRule = rules.snow ?? null;
    const rain = rules.rain !== null && p !== null && p >= rules.rain;
    const wind = rules.wind !== null && w !== null && w >= rules.wind;
    const heat = rules.heat !== null && t !== null && t >= rules.heat;
    const freeze = freezeRule !== null && lo !== null && lo <= freezeRule;
    const snow = snowRule !== null && sn !== null && sn >= snowRule;
    if ((rules.rain !== null && p === null) || (rules.wind !== null && w === null) || (rules.heat !== null && t === null) || (freezeRule !== null && lo === null) || (snowRule !== null && sn === null)) missing++;
    if (rain || wind || heat || freeze || snow) {
      if (freeze) stops.freeze++;
      if (snow) stops.snow++;
      if (rain) { stops.rain++; drying = rules.drying ?? 0; }
      if (wind) stops.wind++;
      if (heat) stops.heat++;
      continue;
    }
    if (drying > 0) { drying--; stops.wet++; continue; }
    if (++done === workdays) {
      const calendarDays = i - startIndex + 1;
      return { year, calendarDays, baselineDays: baselineDays!, extraDays: calendarDays - baselineDays!, stops, missing };
    }
  }
  return null;
}

const median = (v: number[]) => { const s = [...v].sort((a, b) => a - b), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

export function byStartMonth(series: Series, inputs: DelayInputs): { months: MonthSummary[] | null; errors: ReturnType<typeof validate>["errors"]; rulesOff: boolean } {
  const v = validate(inputs);
  const rulesOff = v.rain === null && v.wind === null && v.heat === null && v.freeze === null && v.snow === null;
  if (v.workdays === null || Object.keys(v.errors).length) return { months: null, errors: v.errors, rulesOff };
  const rules = rulesFor(series, v);
  const t0 = parseDay(series.start);
  const firstYear = new Date(t0).getUTCFullYear(), lastYear = new Date(t0 + (series.prcp_in.length - 1) * DAY).getUTCFullYear();
  const months = MONTHS.map((_, month) => {
    const runs: YearRun[] = [], excluded: number[] = [];
    for (let year = firstYear; year <= lastYear; year++) {
      const index = Math.round((Date.UTC(year, month, 1) - t0) / DAY);
      const run = index >= 0 ? replay(series, index, v.workdays!, rules, inputs.weekdaysOnly, year) : null;
      if (run) runs.push(run); else excluded.push(year);
    }
    const extras = runs.map((r) => r.extraDays);
    const worst = runs.reduce<YearRun | null>((a, r) => (!a || r.extraDays > a.extraDays ? r : a), null);
    const lost = runs.reduce((a, r) => a + r.calendarDays - r.baselineDays, 0), total = runs.reduce((a, r) => a + r.calendarDays, 0);
    return {
      month, runs, excluded,
      medianExtra: extras.length ? median(extras) : null, minExtra: extras.length ? Math.min(...extras) : null, maxExtra: extras.length ? Math.max(...extras) : null,
      worstYear: worst?.year ?? null, lostShare: total ? Math.round((lost / total) * 1000) / 1000 : null,
    };
  });
  return { months, errors: v.errors, rulesOff };
}

export function rulesFor(series: Series, v: ReturnType<typeof validate>): Rules {
  return { rain: v.rain, wind: series.wsf2_mph ? v.wind : null, heat: v.heat, drying: v.rain === null ? 0 : v.drying, freeze: series.tmin_f ? v.freeze : null, snow: series.snow_in ? v.snow : null };
}

const isoDay = (t: number) => new Date(t).toISOString().slice(0, 10);
const addDays = (iso: string, n: number) => isoDay(Date.parse(`${iso}T00:00:00Z`) + n * DAY);

export type DateReport = {
  runs: (YearRun & { finish: string; start: string })[];
  excluded: number[];
  baselineDays: number | null;
  medianExtra: number | null;
  worst: (YearRun & { finish: string; start: string }) | null;
  best: (YearRun & { finish: string; start: string }) | null;
  /** The same month-day in the target year, finished after baseline / median / worst extra days. */
  target: { start: string; normalFinish: string | null; typicalFinish: string | null; worstFinish: string | null };
};

/**
 * Replays an exact calendar start date (e.g. 2026-10-14) as if it began on the same month-day in each recorded year.
 * Feb 29 starts use Feb 28 in non-leap years.
 */
export function replayDate(series: Series, startIso: string, inputs: DelayInputs): { report: DateReport | null; errors: ReturnType<typeof validate>["errors"] } {
  const v = validate(inputs);
  if (v.workdays === null || Object.keys(v.errors).length || !/^\d{4}-\d{2}-\d{2}$/.test(startIso)) return { report: null, errors: v.errors };
  const rules = rulesFor(series, v);
  const t0 = parseDay(series.start), md = startIso.slice(5);
  const firstYear = new Date(t0).getUTCFullYear(), lastYear = new Date(t0 + (series.prcp_in.length - 1) * DAY).getUTCFullYear();
  const runs: DateReport["runs"] = [], excluded: number[] = [];
  for (let year = firstYear; year <= lastYear; year++) {
    let start = `${year}-${md}`;
    const parsed = Date.parse(`${start}T00:00:00Z`);
    if (!Number.isFinite(parsed) || isoDay(parsed) !== start) start = `${year}-02-28`; // Feb 29 in a non-leap year
    const index = Math.round((Date.parse(`${start}T00:00:00Z`) - t0) / DAY);
    const run = index >= 0 ? replay(series, index, v.workdays, rules, inputs.weekdaysOnly, year) : null;
    if (run) runs.push({ ...run, start, finish: addDays(start, run.calendarDays - 1) }); else excluded.push(year);
  }
  const extras = runs.map((r) => r.extraDays);
  const worst = runs.reduce<DateReport["worst"]>((a, r) => (!a || r.extraDays > a.extraDays ? r : a), null);
  const best = runs.reduce<DateReport["best"]>((a, r) => (!a || r.extraDays < a.extraDays ? r : a), null);
  // Baseline depends only on weekends, so compute it for the target year itself rather than borrowing a past year's.
  const base = replay({ start: startIso, prcp_in: Array(400).fill(0), tmax_f: Array(400).fill(0), wsf2_mph: null }, 0, v.workdays, { rain: null, wind: null, heat: null }, inputs.weekdaysOnly, 0);
  const medianExtra = extras.length ? median(extras) : null;
  // A weekday-only task cannot finish on a weekend: a median that lands on Sat/Sun rolls to Monday.
  const finish = (extra: number | null) => {
    if (!base || extra === null) return null;
    let t = parseDay(startIso) + (base.calendarDays - 1 + Math.ceil(extra)) * DAY;
    while (inputs.weekdaysOnly && [0, 6].includes(new Date(t).getUTCDay())) t += DAY;
    return isoDay(t);
  };
  return {
    report: { runs, excluded, baselineDays: base?.calendarDays ?? null, medianExtra, worst, best,
      target: { start: startIso, normalFinish: finish(0), typicalFinish: finish(medianExtra), worstFinish: finish(worst?.extraDays ?? null) } },
    errors: v.errors,
  };
}

/** Share of recorded years in which each calendar month-day ("MM-DD") was a stop day under the current rules. */
export function dayRisk(series: Series, inputs: DelayInputs): Map<string, number> {
  const v = validate(inputs);
  const rules = rulesFor(series, v);
  const t0 = parseDay(series.start), counts = new Map<string, [number, number]>();
  for (let i = 0; i < series.prcp_in.length; i++) {
    const md = isoDay(t0 + i * DAY).slice(5);
    const p = series.prcp_in[i], t = series.tmax_f[i], w = series.wsf2_mph?.[i] ?? null, lo = series.tmin_f?.[i] ?? null, sn = series.snow_in?.[i] ?? null;
    const known = p !== null || t !== null;
    if (!known) continue;
    const stop = (rules.rain !== null && p !== null && p >= rules.rain) || (rules.wind !== null && w !== null && w >= rules.wind) || (rules.heat !== null && t !== null && t >= rules.heat)
      || (rules.freeze != null && lo !== null && lo <= rules.freeze) || (rules.snow != null && sn !== null && sn >= rules.snow);
    const c = counts.get(md) ?? [0, 0];
    counts.set(md, [c[0] + (stop ? 1 : 0), c[1] + 1]);
  }
  return new Map([...counts].map(([md, [stops, n]]) => [md, n ? stops / n : 0]));
}
