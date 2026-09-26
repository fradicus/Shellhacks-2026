// CSV building with spreadsheet formula-injection protection. Pure; checked by csv.check.ts.

export type Cell = string | number | boolean | null | undefined;

const FORMULA_START = /^[=+\-@\t\r]/;

/** Text cells starting with = + - @ (or tab/CR) get a leading ' so spreadsheets don't evaluate them.
 * Numbers are emitted as numbers: a negative longitude isn't a formula, and prefixing it would corrupt the data. */
export function cell(v: Cell): string {
  if (v === null || v === undefined) return "";
  let s = typeof v === "number" ? (Number.isFinite(v) ? String(v) : "") : String(v);
  if (typeof v !== "number" && FORMULA_START.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(header: string[], rows: Cell[][]): string {
  return [header, ...rows].map((r) => r.map(cell).join(",")).join("\r\n") + "\r\n";
}
