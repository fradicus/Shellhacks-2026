// Documented history events, derived read-only from the records /time and /explore already serve (F37 part 1).
// Nothing here invents a date, a status or a link: every event is a stored field with its source and locator.
import type { NationalTier } from "../../components/time/nationalProjects";
import type { NationalProject, NationalSource } from "../national/types";
import type { InService, Project, Source, Utility, VersionChange } from "../types";

/** actual: a documented actual in-service/completion date. plan: a documented planned date. other: anything else
 * documented (a certification, say); its sourced description is shown verbatim. */
export type Meaning = "actual" | "plan" | "other";
export type Precision = InService["precision"];

export interface EventSource {
  publisher: string;
  url: string | null;
  locator: string | null;
  retrieved_at: string | null;
  source_date: string | null;
}

export interface HistoryEvent {
  id: string;
  meaning: Meaning;
  label: string;
  /** The publisher's own field name when it has one (PJM `RequiredDate`, ...). */
  field: string | null;
  /** The stored value exactly as published (ISO for exact days, YYYY-MM for months). */
  value: string | null;
  precision: Precision;
  /** Unix days, [from, to): one day for an exact date, the whole month/year otherwise. Null when unknown. */
  from: number | null;
  to: number | null;
  description: string;
  /** A legacy filed date a later filing replaced. */
  superseded: string | null;
  source: EventSource;
}

/** A plan date and a later-documented date on the same project: chronology only, never a duration of work. */
export interface Thread {
  from: string;
  to: string;
  days: number;
  text: string;
}

const LEGACY_FIPS: Partial<Record<Utility, string>> = { DESC: "45", GPC: "13" };

export interface HistoryProject {
  key: string;
  name: string;
  owner: string | null;
  identity: Utility | "national";
  source_id: string;
  source_title: string | null;
  region: string | null;
  /** Stored state FIPS codes (national records; the legacy registers are each one state's filing). */
  states: string[];
  /** Pen colour from the page's state inks, as /time draws it; set by the page. */
  ink?: string;
  /** The publisher's status text as stored (ISO-NE "In-service", PJM "IS"); a status, not an event date. */
  status: string | null;
  center: { lat: number; lon: number } | null;
  /** National points only: how the location was established (C25), as /time draws it. */
  tier?: NationalTier;
  events: HistoryEvent[];
  thread: Thread | null;
}

const DAY_MS = 86_400_000;
const utcDay = (y: number, m: number, d: number) => Date.UTC(y, m - 1, d) / DAY_MS;

/** [from, to) in Unix days for a stored value at its own precision. Never picks a day inside a month or year. */
export function interval(value: string | null, precision: Precision): [number, number] | null {
  if (!value || precision === "unknown") return null;
  const m = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(value);
  if (!m) return null;
  const y = +m[1];
  const mo = m[2] ? +m[2] : null;
  const d = m[3] ? +m[3] : null;
  if (precision === "day") {
    if (mo === null || d === null) return null;
    const day = utcDay(y, mo, d);
    const back = new Date(day * DAY_MS);
    if (back.getUTCMonth() + 1 !== mo || back.getUTCDate() !== d) return null;
    return [day, day + 1];
  }
  if (precision === "month") {
    if (mo === null || mo < 1 || mo > 12) return null;
    return [utcDay(y, mo, 1), utcDay(mo === 12 ? y + 1 : y, mo === 12 ? 1 : mo + 1, 1)];
  }
  return [utcDay(y, 1, 1), utcDay(y + 1, 1, 1)];
}

/** Inclusive-range test in Unix days: an exact date inside it, or any part of a month/year span overlapping it. */
export const intersects = (e: Pick<HistoryEvent, "from" | "to">, lo: number, hiExclusive: number) =>
  e.from !== null && e.to !== null && e.from < hiExclusive && e.to > lo;

// PJM register date fields: the name as published, what it means, and which plan field a bracket prefers.
const PJM: Record<string, { label: string; meaning: Meaning }> = {
  ActualInServiceDate: { label: "Actual in-service date", meaning: "actual" },
  RequiredDate: { label: "Required date", meaning: "plan" },
  ProjectedInServiceDate: { label: "Projected in-service date", meaning: "plan" },
  RevisedInServiceDate: { label: "Revised in-service date", meaning: "plan" },
  ISAInServiceDate: { label: "ISA in-service date", meaning: "plan" },
};
const PLAN_PREFERENCE = ["RequiredDate", "ProjectedInServiceDate", "RevisedInServiceDate", "ISAInServiceDate"];
type StoredEvent = NonNullable<NationalProject["location_verification"]>["events"][number];
const TYPE: Record<StoredEvent["type"], { label: string; meaning: Meaning }> = {
  in_service: { label: "In service", meaning: "actual" },
  completion: { label: "Completion", meaning: "actual" },
  planned_milestone: { label: "Planned milestone", meaning: "plan" },
  certification: { label: "Certification", meaning: "other" },
  award: { label: "Award", meaning: "other" },
  construction_start: { label: "Construction start", meaning: "other" },
  cancellation: { label: "Cancellation", meaning: "other" },
  source_status: { label: "Source status", meaning: "other" },
};

const plural = (n: number, w: string) => `${n.toLocaleString("en-US")} ${w}${n === 1 ? "" : "s"}`;

function planActualThread(events: HistoryEvent[]): Thread | null {
  const actual = events.find((e) => e.meaning === "actual" && e.precision === "day" && e.from !== null);
  if (!actual) return null;
  for (const field of PLAN_PREFERENCE) {
    const plan = events.find((e) => e.field === field && e.precision === "day" && e.from !== null);
    if (!plan) continue;
    const days = actual.from! - plan.from!;
    const when = days === 0 ? "on" : `${plural(Math.abs(days), "day")} ${days > 0 ? "after" : "before"}`;
    return { from: plan.id, to: actual.id, days, text: `In service ${when} the ${plan.label.toLowerCase()}` };
  }
  return null;
}

const byDate = (a: HistoryEvent, b: HistoryEvent) =>
  (a.from ?? Infinity) - (b.from ?? Infinity) || a.id.localeCompare(b.id);

/** Events for one active national record: its published `project_events`, else its stored in-service value. */
export function nationalHistory(p: NationalProject, source: NationalSource | undefined): HistoryProject {
  const stored = ((p as NationalProject & { project_events?: StoredEvent[] }).project_events ?? []) as StoredEvent[];
  const events: HistoryEvent[] = stored.map((e) => {
    const field = e.id.split(":").pop() ?? null;
    const known = field && PJM[field] ? PJM[field] : TYPE[e.type] ?? { label: e.type, meaning: "other" as const };
    const span = interval(e.date, e.precision);
    const ev = e.evidence[0];
    return {
      id: e.id,
      meaning: known.meaning,
      label: known.label,
      field: field && PJM[field] ? field : null,
      value: e.date,
      precision: e.precision,
      from: span?.[0] ?? null,
      to: span?.[1] ?? null,
      description: e.description,
      superseded: null,
      source: {
        publisher: ev?.publisher ?? source?.publisher ?? "Publisher not recorded",
        url: ev?.url ?? source?.landing_url ?? null,
        locator: ev?.locator ?? null,
        retrieved_at: ev?.retrieved_at ?? source?.retrieved_at ?? null,
        source_date: ev?.source_date ?? null,
      },
    };
  });
  if (!events.length && (p.in_service.value || p.in_service.raw)) {
    // No event list: the record's own in-service value. ISO-NE publishes it as a projected month.
    const isoNe = p.planning_region === "iso-ne";
    const span = interval(p.in_service.value, p.in_service.precision);
    events.push({
      id: `${p._id}:in_service`,
      meaning: isoNe ? "plan" : "other",
      label: isoNe ? "Projected in-service month" : "Published in-service value",
      field: isoNe ? "Projected In-Service Month/Year" : null,
      value: p.in_service.value,
      precision: p.in_service.precision,
      from: span?.[0] ?? null,
      to: span?.[1] ?? null,
      description: isoNe
        ? `Projected in-service month as listed; the register's status is "${p.status ?? "not stated"}". Not an actual in-service date.`
        : `In-service value as published (raw "${p.in_service.raw ?? "none"}"); the source does not say whether it is planned or actual.`,
      superseded: null,
      source: {
        publisher: source?.publisher ?? "Publisher not recorded",
        url: source?.landing_url ?? source?.download_url ?? null,
        locator: [p.evidence.sheet, p.evidence.row !== null ? `row ${p.evidence.row}` : null, p.evidence.page !== null ? `p. ${p.evidence.page}` : null]
          .filter(Boolean).join(" · ") || null,
        retrieved_at: source?.retrieved_at ?? null,
        source_date: source?.publication_date ?? null,
      },
    });
  }
  events.sort(byDate);
  return {
    key: p._id,
    name: p.name,
    owner: p.owner,
    identity: "national",
    source_id: p.source_id,
    source_title: source?.title ?? null,
    region: p.planning_region,
    states: p.states ?? [],
    status: p.status,
    center: p.center ? { lat: p.center.lat, lon: p.center.lon } : null,
    events,
    thread: planActualThread(events),
  };
}

const UTILITY: Record<Utility, string> = { DESC: "Dominion Energy SC", GPC: "Georgia Power", unknown: "Owner not mapped" };

/** A legacy filing's current milestone, plus every earlier filed date F14 recorded for it. */
export function legacyHistory(p: Project, changes: VersionChange[], sources: Map<string, Source>): HistoryProject {
  const src = (id: string, page: number | null | undefined): EventSource => ({
    publisher: sources.get(id)?.publisher ?? id,
    url: sources.get(id)?.url ?? null,
    locator: `${id}${page != null ? ` p. ${page}` : ""}`,
    retrieved_at: sources.get(id)?.retrieved_at ?? null,
    source_date: null,
  });
  const span = interval(p.in_service.date, p.in_service.precision);
  const current: HistoryEvent = {
    id: `${p.project_key}:filed:${p.source.source_id}`,
    meaning: "plan",
    label: "Filed in-service milestone",
    field: null,
    value: p.in_service.date,
    precision: p.in_service.precision,
    from: span?.[0] ?? null,
    to: span?.[1] ?? null,
    description: `Filed as “${p.in_service.raw ?? "no date"}” in ${p.source.source_id}. A filed milestone, not proof of completion.`,
    superseded: null,
    source: src(p.source.source_id, p.source.page),
  };
  const events = [current];
  let thread: Thread | null = null;
  for (const c of changes) {
    if (c.project_key !== p.project_key || c.field !== "in_service.date" || typeof c.old !== "string") continue;
    const old = /^\d{4}-\d{2}-\d{2}$/.test(c.old) ? interval(c.old, "day") : null;
    const ev: HistoryEvent = {
      id: c._id,
      meaning: "plan",
      label: "Earlier filed milestone",
      field: null,
      value: c.old,
      precision: old ? "day" : "unknown",
      from: old?.[0] ?? null,
      to: old?.[1] ?? null,
      description: `Filed as ${c.old} in ${c.from_source}; ${c.to_source} files ${String(c.new)}.`,
      superseded: c.to_source,
      source: src(c.from_source, c.from_page),
    };
    events.push(ev);
    if (old && current.from !== null && current.precision === "day" && c.to_source === p.source.source_id) {
      const days = current.from - old[0];
      thread = {
        from: ev.id,
        to: current.id,
        days,
        text: days === 0 ? `Refiled on the same date in ${c.to_source}` : `Moved ${plural(Math.abs(days), "day")} ${days > 0 ? "later" : "earlier"} between ${c.from_source} and ${c.to_source}`,
      };
    }
  }
  events.sort(byDate);
  return {
    key: p.project_key,
    name: p.name,
    owner: p.utility === "unknown" && p.owner_code ? `Owner code ${p.owner_code}, not mapped` : UTILITY[p.utility],
    identity: p.utility,
    source_id: p.source.source_id,
    source_title: sources.get(p.source.source_id)?.title ?? null,
    region: p.state ?? null,
    states: LEGACY_FIPS[p.utility] ? [LEGACY_FIPS[p.utility]!] : [],
    status: p.status ?? null,
    center: p.center ? { lat: p.center.lat, lon: p.center.lon } : null,
    events,
    thread,
  };
}

/** Great-circle miles between two stored centers. History's "near this project" research aid only: it never feeds
 * a stored distance, overlap or rank. */
export function milesBetween(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180;
  const h = Math.sin(((b.lat - a.lat) * r) / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2;
  return 2 * 3958.7613 * Math.asin(Math.min(1, Math.sqrt(h)));
}
