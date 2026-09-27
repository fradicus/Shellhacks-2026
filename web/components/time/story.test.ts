import assert from "node:assert/strict";
import test from "node:test";
import { pickStoryPairs } from "./story";
import type { TimePair } from "./TimeView";

const pair = (id: string, a: string, b: string, distance_mi: number, time_gap_days: number | null): TimePair =>
  ({ id, a, b, distance_mi, time_gap_days, band: 0, view: "tentative", rank: null, candidate: true, review_state: null });

// North Dakota's candidates at dataset 489d9c2 (distances rounded), the ones F53 was designed on.
const nd = [
  pair("npc:b2bb", "williston", "patent-gate-pioneer-line", 6.47, 1157),
  pair("npc:4614", "tableland-wheelock", "williston", 23.86, 1),
  pair("npc:7ffc", "wheelock-terminal", "williston", 23.86, 1),
  pair("npc:2752", "williston", "pioneer-115", 12.2, 823),
  pair("npc:19ad", "williston", "pioneer-345", 12.2, 1157),
  pair("npc:b2c2", "williston", "patent-gate-345", 22.7, 1157),
  pair("npc:0050", "roughrider", "leland-olds", 19.8, 1050),
  pair("npc:9999", "saluda", "batesburg", 12.93, null),
];

test("the pair is the smallest known gap, ties broken by distance then id", () => {
  assert.equal(pickStoryPairs(nd)?.lead.id, "npc:4614");
});

test("the contrast shares a project, is nearer, and has the widest gap (nearest on ties)", () => {
  assert.equal(pickStoryPairs(nd)?.contrast?.id, "npc:b2bb");
});

test("no nearer kin: the widest-gap kin; no kin: no contrast; no known gap: nothing", () => {
  const far = [pair("l", "x", "y", 1, 5), pair("k", "y", "z", 9, 400), pair("j", "x", "w", 9, 90)];
  assert.equal(pickStoryPairs(far)?.contrast?.id, "k");
  assert.equal(pickStoryPairs([pair("l", "x", "y", 1, 5), pair("o", "p", "q", 0.5, 900)])?.contrast, null);
  assert.equal(pickStoryPairs([pair("u", "x", "y", 1, null)]), null);
});
