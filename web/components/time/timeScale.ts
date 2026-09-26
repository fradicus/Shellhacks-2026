// Pure time-axis math for the time view. Height is display only: it never feeds distance, overlap or ranking.
import type { InService } from "@/lib/types";

const DAY_MS = 86_400_000;
export const DAYS_PER_YEAR = 365.25;

/** Where a filed in-service date sits on the vertical axis, in days since the axis epoch.
 * exact: a filed calendar day. range: the filing gives only a month or a year, so the date is somewhere inside
 * [from, to) and we draw the whole span rather than pick a day. unknown: no height at all. */
export type Span =
  | { kind: "exact"; day: number; iso: string }
  | { kind: "range"; from: number; to: number; precision: "month" | "year"; label: string }
  | { kind: "unknown" };

const utcDay = (y: number, m: number, d: number) => Date.UTC(y, m - 1, d) / DAY_MS;

function parts(iso: string | null): [number, number, number] | null {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso) : null;
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

/** The axis ground: 1 January of the earliest year drawn. Declared on screen; it is an axis origin, not a date
 * assigned to any project. */
export function epochYear(spans: InService[]): number {
  const years = spans.map((s) => parts(s.date)?.[0]).filter((y): y is number => y !== undefined);
  return years.length ? Math.min(...years) : new Date().getUTCFullYear();
}

export function span(s: InService, epoch: number): Span {
  const p = parts(s.date);
  if (!p) return { kind: "unknown" };
  const [y, m, d] = p;
  const base = utcDay(epoch, 1, 1);
  if (s.precision === "day") return { kind: "exact", day: utcDay(y, m, d) - base, iso: s.date! };
  if (s.precision === "month")
    return {
      kind: "range",
      from: utcDay(y, m, 1) - base,
      to: utcDay(m === 12 ? y + 1 : y, m === 12 ? 1 : m + 1, 1) - base,
      precision: "month",
      label: `${y}-${String(m).padStart(2, "0")}`,
    };
  if (s.precision === "year")
    return { kind: "range", from: utcDay(y, 1, 1) - base, to: utcDay(y + 1, 1, 1) - base, precision: "year", label: String(y) };
  return { kind: "unknown" };
}

/** Day offset of an ISO date (the analysis date, for the "today" plane). */
export function dayOf(iso: string, epoch: number): number {
  const p = parts(iso);
  return p ? utcDay(...p) - utcDay(epoch, 1, 1) : 0;
}

/** Ground metres per screen pixel at a latitude and MapLibre zoom (512-px tiles). */
export function metersPerPixel(lat: number, zoom: number): number {
  return (40_075_016.686 * Math.cos((lat * Math.PI) / 180)) / (512 * 2 ** zoom);
}

export const fmtDays = (d: number) => `${d.toLocaleString("en-US")} day${d === 1 ? "" : "s"}`;
