// The /time story (F53): its beats and the rule that picks its two pairs. Display only; nothing here ranks or changes a pair.
import type { TimePair } from "./TimeView";

/** The one thing the story names: North Dakota (FIPS 38). Its pairs are picked by rule from the stored candidates. */
export const STORY_STATE = "38";
export const BEATS = [
  { id: "nation", ms: 7000 },
  { id: "region", ms: 4000 },
  { id: "state", ms: 4000 },
  { id: "pair", ms: 5000 },
  { id: "evidence", ms: 5000 },
  { id: "contrast", ms: 6000 },
  { id: "out", ms: 4000 },
] as const;
export type BeatId = (typeof BEATS)[number]["id"];
/**
 * F53: the best-timed pair (smallest known gap, then nearer, then id), and a contrast that shares a project with it:
 * nearer on the ground with the widest gap, else the widest gap. Null when no pair has a known gap.
 */
export function pickStoryPairs(pairs: TimePair[]): { lead: TimePair; contrast: TimePair | null } | null {
  const dated = pairs.filter((p) => p.time_gap_days !== null);
  const byId = (x: TimePair, y: TimePair) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0);
  const lead = [...dated].sort((x, y) => x.time_gap_days! - y.time_gap_days! || x.distance_mi - y.distance_mi || byId(x, y))[0];
  if (!lead) return null;
  const kin = dated.filter((p) => p.id !== lead.id && p.time_gap_days! > lead.time_gap_days! && [p.a, p.b].some((k) => k === lead.a || k === lead.b));
  const widest = (ps: TimePair[]) => [...ps].sort((x, y) => y.time_gap_days! - x.time_gap_days! || x.distance_mi - y.distance_mi || byId(x, y))[0] ?? null;
  return { lead, contrast: widest(kin.filter((p) => p.distance_mi < lead.distance_mi)) ?? widest(kin) };
}
