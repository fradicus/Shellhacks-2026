// Scope: which part of the map is lifted. Membership reads stored facts only (F19 spec 15–21).
import type { TimeProject } from "./TimeView";

export type Scope = { kind: "region" | "state" | "plan"; code: string } | { kind: "pin"; lat: number; lon: number };
export interface ScopeState { fips: string; name: string; usps: string; region: string }
export interface ScopeGeography { states: ScopeState[]; regions: { code: string; name: string }[] }

/** The overlap rule's radius and the matcher's earth radius (pipeline/matches/core.py), so a pin agrees with pairs. */
export const RULE_MI = 25;
const EARTH_RADIUS_MI = 3958.8;

export function haversineMi(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = Math.PI / 180;
  const h = Math.sin(((lat2 - lat1) * r) / 2) ** 2
    + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 2 * EARTH_RADIUS_MI * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h))));
}

/** Legacy registers are each one state's filing (F01, F02); the sample fixture has none. */
const LEGACY_STATE: [prefix: string, fips: string][] = [["desc-", "45"], ["gpc-", "13"]];
export function statesOf(p: TimeProject): string[] {
  if (p.national) return p.national.project.states;
  const hit = LEGACY_STATE.find(([prefix]) => p.source_id.startsWith(prefix));
  return hit ? [hit[1]] : [];
}

/**
 * Stored planning label, grouped case-insensitively ("PJM" and "pjm" are one plan). Only the plans named below count:
 * some imports stored a document's section heading in the field ("terminal facilities; bpa"), which is not a plan.
 */
export const planOf = (p: TimeProject) => {
  const code = p.national?.project.planning_region?.trim().toLowerCase();
  return code && Object.hasOwn(PLAN_NAME, code) ? code : null;
};
const PLAN_NAME: Record<string, string> = {
  ercot: "ERCOT", nyiso: "NYISO", frcc: "FRCC", "atc-tya": "ATC 10-year", miso: "MISO", "mn-biennial": "Minnesota biennial",
  pjm: "PJM", "iso-ne": "ISO-NE", nypsc: "NY PSC", caiso: "CAISO", spp: "SPP", sertp: "SERTP", scrtp: "SCRTP",
  northerngrid: "NorthernGrid", westconnect: "WestConnect",
};
export const planName = (code: string) => PLAN_NAME[code] ?? code;

export function inScope(p: TimeProject, scope: Scope, regionOf: Map<string, string>): boolean {
  if (!p.center) return false;
  switch (scope.kind) {
    case "pin": return haversineMi(scope.lat, scope.lon, p.center.lat, p.center.lon) <= RULE_MI;
    case "plan": return planOf(p) === scope.code;
    case "state": return statesOf(p).includes(scope.code);
    case "region": return statesOf(p).some((s) => regionOf.get(s) === scope.code);
  }
}

/** `region:3`, `state:48`, `plan:ercot`, `pin:29.7604,-95.3698`; anything else is null. */
export function parseScope(raw: string | null): Scope | null {
  const m = raw?.match(/^(region|state|plan|pin):(.+)$/);
  if (!m) return null;
  const [, kind, code] = m;
  if (kind === "region") return /^[1-4]$/.test(code) ? { kind, code } : null;
  if (kind === "state") return /^\d{2}$/.test(code) ? { kind, code } : null;
  if (kind === "plan") return Object.hasOwn(PLAN_NAME, code) ? { kind, code } : null;
  const ll = code.match(/^(-?\d{1,3}(?:\.\d+)?),(-?\d{1,3}(?:\.\d+)?)$/);
  const [lat, lon] = [Number(ll?.[1]), Number(ll?.[2])];
  return ll && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { kind: "pin", lat, lon } : null;
}

export const formatScope = (s: Scope) =>
  s.kind === "pin" ? `pin:${s.lat.toFixed(4)},${s.lon.toFixed(4)}` : `${s.kind}:${s.code}`;

export function scopeName(s: Scope, geo: ScopeGeography): string {
  if (s.kind === "pin") return `Within ${RULE_MI} mi of pin`;
  if (s.kind === "plan") return planName(s.code);
  if (s.kind === "state") return geo.states.find((x) => x.fips === s.code)?.name ?? `State ${s.code}`;
  return `${geo.regions.find((x) => x.code === s.code)?.name ?? `Region ${s.code}`} region`;
}
