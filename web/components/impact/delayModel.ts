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

export type Series = { start: string; prcp_in: (number | null)[]; tmax_f: (number | null)[]; wsf2_mph: (number | null)[] | null };
export type DelayInputs = { workdays: string; weekdaysOnly: boolean; rainIn: string; windMph: string; heatF: string };
/**
 * Visible, editable stop rules. Rain 0.50 in is a standard NOAA climate-normals day-count threshold; wind 28 mph is the
 * 12.5 m/s rated-wind limit for aerial work platforms in ANSI/SAIA A92.20. Heat has no common stop rule, so it starts off.
 */
export const DEFAULT_DELAY: DelayInputs = { workdays: "20", weekdaysOnly: true, rainIn: "0.50", windMph: "28", heatF: "" };

export type YearRun = { year: number; calendarDays: number; baselineDays: number; extraDays: number; stops: { rain: number; wind: number; heat: number }; missing: number };
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
  if (rain.error) errors.rainIn = rain.error;
  if (wind.error) errors.windMph = wind.error;
  if (heat.error) errors.heatF = heat.error;
  return { errors, workdays: errors.workdays ? null : Number(n), rain: rain.value, wind: wind.value, heat: heat.value };
}

/** Replays one start date. Returns null when the record ends before the task would have finished. */
export function replay(series: Series, startIndex: number, workdays: number, rules: { rain: number | null; wind: number | null; heat: number | null }, weekdaysOnly: boolean, year: number): YearRun | null {
  const t0 = parseDay(series.start);
  const length = series.prcp_in.length;
  let done = 0, base = 0, baselineDays: number | null = null, missing = 0;
  const stops = { rain: 0, wind: 0, heat: 0 };
  for (let i = startIndex; i < length; i++) {
    const weekday = new Date(t0 + i * DAY).getUTCDay();
    if (weekdaysOnly && (weekday === 0 || weekday === 6)) continue;
    if (baselineDays === null && ++base === workdays) baselineDays = i - startIndex + 1;
    const p = series.prcp_in[i], t = series.tmax_f[i], w = series.wsf2_mph?.[i] ?? null;
    const rain = rules.rain !== null && p !== null && p >= rules.rain;
    const wind = rules.wind !== null && w !== null && w >= rules.wind;
    const heat = rules.heat !== null && t !== null && t >= rules.heat;
    if ((rules.rain !== null && p === null) || (rules.wind !== null && w === null) || (rules.heat !== null && t === null)) missing++;
    if (rain || wind || heat) {
      if (rain) stops.rain++;
      if (wind) stops.wind++;
      if (heat) stops.heat++;
      continue;
    }
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
  const rulesOff = v.rain === null && v.wind === null && v.heat === null;
  if (v.workdays === null || Object.keys(v.errors).length) return { months: null, errors: v.errors, rulesOff };
  const rules = { rain: v.rain, wind: series.wsf2_mph ? v.wind : null, heat: v.heat };
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
