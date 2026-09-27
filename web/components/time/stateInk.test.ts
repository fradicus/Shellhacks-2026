import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { INKS, neighborColors, stateInks, type StateFeature } from "./stateInk";

const { features } = JSON.parse(readFileSync(new URL("./usStates.json", import.meta.url), "utf8")) as { features: StateFeature[] };
const byUsps = new Map(features.map((f) => [f.properties.STUSAB, f.properties.GEOID]));

test("every state gets a palette color and no two neighbors share one", () => {
  const color = neighborColors(features);
  assert.equal(features.length, 51);
  assert.equal(color.size, 51);
  for (const c of color.values()) assert.ok(c >= 0 && c < INKS.length);
  // Real borders from the committed file, including a four-corners touch (CO/AZ) and DC.
  for (const [a, b] of [["TX", "OK"], ["TX", "LA"], ["GA", "FL"], ["MI", "WI"], ["CO", "AZ"], ["DC", "MD"], ["NY", "VT"], ["TN", "MO"]])
    assert.notEqual(color.get(byUsps.get(a)!), color.get(byUsps.get(b)!), `${a}/${b}`);
  // Exhaustive: any shared border vertex means different colors.
  const owners = new Map<string, string[]>();
  for (const f of features) {
    const g = f.geometry;
    for (const ring of (g.type === "Polygon" ? [g.coordinates] : g.coordinates).flat())
      for (const [x, y] of ring) owners.set(`${x},${y}`, [...(owners.get(`${x},${y}`) ?? []), f.properties.GEOID]);
  }
  for (const ids of owners.values()) assert.equal(new Set(ids.map((id) => color.get(id))).size, new Set(ids).size);
});

test("colors are spread, not piled on the first one", () => {
  const counts = Array(INKS.length).fill(0);
  for (const c of neighborColors(features).values()) counts[c]++;
  assert.ok(Math.min(...counts) >= 6, `counts ${counts}`);
});

test("stateInks maps every state to an ink", () => {
  const inks = stateInks(features);
  assert.equal(inks["48"] !== undefined && INKS.includes(inks["48"]), true);
  assert.notEqual(inks["48"], inks["40"]); // Texas / Oklahoma
  assert.equal(Object.keys(inks).length, 51);
});
