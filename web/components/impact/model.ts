export const SCENARIOS = ["Low", "Base", "High"] as const;
export type ScenarioName = (typeof SCENARIOS)[number];
export type Inputs = {
  mobilizations: string;
  unitCost: string;
  coordinationCost: string;
  idleDays: string;
  dailyRate: string;
};
export const emptyInputs = (): Inputs => ({ mobilizations: "", unitCost: "", coordinationCost: "", idleDays: "", dailyRate: "" });

/** Values are user assumptions. Money is calculated in integer cents; blanks never become zero. */
export function inputError(value: string, money: boolean): string | null {
  if (!value.trim()) return null;
  const format = money ? /^\d+(\.\d{1,2})?$/ : /^\d+$/;
  if (!format.test(value.trim())) return money ? "Enter a nonnegative amount with up to 2 decimals." : "Enter a nonnegative whole number.";
  if (Number(value) > (money ? 1_000_000_000 : 1_000_000)) return "Amount is too large for this worksheet.";
  return null;
}

export function calculate(inputs: Inputs, holding: boolean) {
  const keys: (keyof Inputs)[] = ["mobilizations", "unitCost", "coordinationCost", ...(holding ? ["idleDays", "dailyRate"] as const : [])];
  const errors = Object.fromEntries(keys.flatMap((key) => {
    const error = inputError(inputs[key], key !== "mobilizations" && key !== "idleDays");
    return error ? [[key, error]] : [];
  })) as Partial<Record<keyof Inputs, string>>;
  const missing = keys.filter((key) => !inputs[key].trim()).length;
  if (missing || Object.keys(errors).length) return { result: null, errors, missing, overflow: false };

  const cents = (value: string) => Math.round(Number(value) * 100);
  const avoided = Number(inputs.mobilizations) * cents(inputs.unitCost);
  const coordination = cents(inputs.coordinationCost);
  const dailyRate = holding ? cents(inputs.dailyRate) : 0;
  const carrying = holding ? Number(inputs.idleDays) * dailyRate : 0;
  const costs = coordination + carrying;
  const net = avoided - costs;
  if (![avoided, coordination, carrying, costs, net].every(Number.isSafeInteger)) {
    return { result: null, errors, missing: 0, overflow: true };
  }
  const maxIdleDays = holding && dailyRate > 0 && avoided >= coordination
    ? Math.floor((avoided - coordination) / dailyRate)
    : null;
  return { result: { avoided, coordination, carrying, costs, net, maxIdleDays }, errors, missing: 0, overflow: false };
}

export function money(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** ISO dates only; UTC arithmetic preserves leap days and ignores daylight-saving changes. */
export function milestoneGap(a: string, b: string): number | null {
  const parse = (value: string) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return null;
    const time = Date.parse(`${value}T00:00:00Z`);
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? time : null;
  };
  const first = parse(a), second = parse(b);
  return first === null || second === null ? null : Math.abs(first - second) / 86_400_000;
}
