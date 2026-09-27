// Plan against record: how far each documented actual in-service date fell from the same row's required date.

/** Half-year bins, clamped at three years either side; the end bins also hold everything beyond. */
export const SLIP_BIN_DAYS = 182.625;
export const SLIP_SPAN = 6;

export interface SlipBins {
  /** Count per bin, earliest first: bins [0, SLIP_SPAN) are early, [SLIP_SPAN, 2·SLIP_SPAN) are on time or late. */
  counts: number[];
  early: number;
  late: number;
  /** Median of the signed day gaps (negative = before the required date); null with no rows. */
  median: number | null;
}

export function slipBins(days: number[]): SlipBins {
  const counts = Array<number>(SLIP_SPAN * 2).fill(0);
  for (const d of days) {
    const i = Math.floor(d / SLIP_BIN_DAYS) + SLIP_SPAN;
    counts[Math.min(Math.max(i, 0), SLIP_SPAN * 2 - 1)]++;
  }
  const sorted = [...days].sort((a, b) => a - b);
  const mid = sorted.length >> 1;
  const median = !sorted.length ? null : sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return { counts, early: days.filter((d) => d < 0).length, late: days.filter((d) => d > 0).length, median };
}
