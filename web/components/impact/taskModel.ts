/**
 * Site-factor task cost (user scenario). Crews and equipment are billed for the whole shift but only produce while
 * the site window is open (tide, daylight, flood stage). A shorter window therefore adds paid days, not a higher rate.
 *
 *   C_task = work_days × paid_hours_per_day × (labor + equipment rate) × site multiplier + permit cost + dead_days × standby rate
 *
 * Every input is user-entered or copied from a cited quote. There are no default rates or multiplier tables; blank
 * inputs keep the result null. Money is integer cents.
 */
export type TaskInputs = {
  productiveHours: string;
  paidHoursPerDay: string;
  laborRate: string;
  equipRate: string;
  siteMultiplier: string;
  siteBasis: string;
  permitCost: string;
  standbyPerDay: string;
  windows: string;
};
export const emptyTask = (): TaskInputs => ({ productiveHours: "", paidHoursPerDay: "", laborRate: "", equipRate: "", siteMultiplier: "", siteBasis: "", permitCost: "", standbyPerDay: "", windows: "" });

export type ShareInputs = { itemCost: string; shareA: string; shareB: string; separateA: string; separateB: string };
export const emptyShare = (): ShareInputs => ({ itemCost: "", shareA: "", shareB: "", separateA: "", separateB: "" });

const MONEY = /^\d+(\.\d{1,2})?$/;
const DECIMAL = /^\d+(\.\d{1,2})?$/;
const MAX_MONEY = 1_000_000_000;
const MAX_DAYS = 366;

type Kind = "money" | "hours" | "multiplier" | "weight";
function check(value: string, kind: Kind): string | null {
  const v = value.trim();
  if (!v) return null;
  if (!(kind === "money" ? MONEY : DECIMAL).test(v)) return kind === "money" ? "Enter a nonnegative amount with up to 2 decimals." : "Enter a nonnegative number with up to 2 decimals.";
  const n = Number(v);
  if (kind === "money" && n > MAX_MONEY) return "Amount is too large for this worksheet.";
  if (kind === "hours" && (n <= 0 || n > 24)) return "Enter hours between 0 and 24.";
  if (kind === "multiplier" && (n < 1 || n > 10)) return "Enter a multiplier from 1.00 to 10.00.";
  if (kind === "weight" && n > 1_000_000) return "Share is too large.";
  return null;
}
const cents = (value: string) => Math.round(Number(value) * 100);
/** Hundredths as an integer so the multiplier is applied without binary rounding drift. */
const hundredths = (value: string) => Math.round(Number(value) * 100);

/** Comma/space/newline separated usable hours per calendar day, in order. 0 is an explicit closed day. */
export function parseWindows(text: string): { hours: number[] | null; error: string | null } {
  const parts = text.split(/[\s,;]+/).filter(Boolean);
  if (!parts.length) return { hours: null, error: null };
  if (parts.length > MAX_DAYS) return { hours: null, error: `Enter at most ${MAX_DAYS} days.` };
  const bad = parts.find((p) => !/^\d+(\.\d{1,2})?$/.test(p) || Number(p) > 24);
  if (bad !== undefined) return { hours: null, error: `"${bad.slice(0, 12)}" is not 0–24 hours with up to 2 decimals.` };
  return { hours: parts.map(Number), error: null };
}

const TASK_FIELDS: [keyof TaskInputs, Kind][] = [["productiveHours", "weight"], ["paidHoursPerDay", "hours"], ["laborRate", "money"], ["equipRate", "money"], ["siteMultiplier", "multiplier"], ["permitCost", "money"], ["standbyPerDay", "money"]];

export function calculateTask(inputs: TaskInputs) {
  const errors: Partial<Record<keyof TaskInputs, string>> = {};
  for (const [key, kind] of TASK_FIELDS) { const e = check(inputs[key], kind); if (e) errors[key] = e; }
  if (inputs.productiveHours.trim() && !errors.productiveHours && Number(inputs.productiveHours) <= 0) errors.productiveHours = "Enter more than 0 hours.";
  const windows = parseWindows(inputs.windows);
  if (windows.error) errors.windows = windows.error;
  const missing = TASK_FIELDS.filter(([key]) => !inputs[key].trim()).length + (windows.hours ? 0 : 1) + (inputs.siteBasis.trim() ? 0 : 1);
  if (missing || Object.keys(errors).length) return { result: null, errors, missing, shortfallHours: null as number | null, overflow: false };

  const need = Number(inputs.productiveHours), shift = Number(inputs.paidHoursPerDay);
  let remaining = Math.round(need * 100), workDays = 0, deadDays = 0; // hundredths of an hour
  for (const hours of windows.hours!) {
    if (remaining <= 0) break;
    const usable = Math.round(Math.min(hours, shift) * 100);
    if (usable <= 0) deadDays++; else { workDays++; remaining -= usable; }
  }
  if (remaining > 0) return { result: null, errors, missing: 0, shortfallHours: remaining / 100, overflow: false };

  const hourly = cents(inputs.laborRate) + cents(inputs.equipRate);
  const shiftHundredths = Math.round(shift * 100);
  const paidCrew = Math.round(workDays * shiftHundredths * hourly / 100);
  const siteAdjusted = Math.round(paidCrew * hundredths(inputs.siteMultiplier) / 100);
  const siteExtra = siteAdjusted - paidCrew;
  const permit = cents(inputs.permitCost);
  const standby = deadDays * cents(inputs.standbyPerDay);
  const total = siteAdjusted + permit + standby;
  // Cost of the restricted window alone: paid-but-idle shift hours plus closed days, before the site multiplier.
  const idleHours = (workDays * shiftHundredths - Math.round(need * 100)) / 100;
  if (![paidCrew, siteAdjusted, siteExtra, permit, standby, total].every(Number.isSafeInteger)) return { result: null, errors, missing: 0, shortfallHours: null, overflow: true };
  return {
    result: { workDays, deadDays, calendarDays: workDays + deadDays, paidCrew, siteAdjusted, siteExtra, permit, standby, total, idleHours: Math.max(0, idleHours), windowFactor: Math.round((need / (workDays * shift)) * 1000) / 1000 },
    errors, missing: 0, shortfallHours: null, overflow: false,
  };
}

/** Largest-remainder pro-rata split so the parts always sum to the whole, in cents. */
export function splitProRata(totalCents: number, weights: number[]): number[] {
  const sum = weights.reduce((a, b) => a + b, 0);
  if (!(sum > 0)) return weights.map(() => 0);
  const raw = weights.map((w) => (totalCents * w) / sum);
  const out = raw.map(Math.floor);
  const order = raw.map((r, i) => [r - out[i], i] as const).sort((a, b) => b[0] - a[0] || a[1] - b[1]);
  for (let k = 0; k < totalCents - out.reduce((a, b) => a + b, 0); k++) out[order[k % out.length][1]]++;
  return out;
}

export function calculateShare(inputs: ShareInputs) {
  const kinds: [keyof ShareInputs, Kind][] = [["itemCost", "money"], ["shareA", "weight"], ["shareB", "weight"], ["separateA", "money"], ["separateB", "money"]];
  const errors: Partial<Record<keyof ShareInputs, string>> = {};
  for (const [key, kind] of kinds) { const e = check(inputs[key], kind); if (e) errors[key] = e; }
  const required: (keyof ShareInputs)[] = ["itemCost", "shareA", "shareB"];
  const missing = required.filter((key) => !inputs[key].trim()).length;
  if (!errors.shareA && !errors.shareB && inputs.shareA.trim() && inputs.shareB.trim() && Number(inputs.shareA) + Number(inputs.shareB) <= 0) errors.shareB = "At least one share must be above 0.";
  if (missing || Object.keys(errors).length) return { result: null, errors, missing };
  const [a, b] = splitProRata(cents(inputs.itemCost), [Number(inputs.shareA), Number(inputs.shareB)]);
  // The comparison exists only when the user entered what each utility would pay to build alone.
  const diff = (separate: string, share: number) => separate.trim() ? cents(separate) - share : null;
  return { result: { a, b, differenceA: diff(inputs.separateA, a), differenceB: diff(inputs.separateB, b) }, errors, missing: 0 };
}
