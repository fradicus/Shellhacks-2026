import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";
const root = new URL("../../../web/", import.meta.url);
let active = "test:A", ready = true, fail = false, missingProject = false;
let reads = 0;
let lastFilter: Record<string, unknown> = {};
const candidate = { id: `npc:${"a".repeat(32)}`, a: "p1", b: "p2", distance_mi: 2, drive_mi: 3, time_gap_days: null,
  route: { polyline: "_p~iF~ps|U", start: null, end: null, provider: "test", data_source: "test", computed_at: "2026-09-27T00:00:00Z",
    duration_s: 60 },
  band: 0, rank: 1, tier: "tentative", rule_version: "national-drive-25mi-v1", identity_version: "test" };
let rows = [candidate];
const project = (id: string) => ({ id, name: id, source_id: "test", native_id: id, owner: "Test", other_owners: [],
  center: { lat: 30, lon: -95, basis: "one", evidence: "test only" }, states: ["48"], counties: [],
  location_review: "unreviewed", status_group: "planned", evidence: { page: 1, sheet: null, row: null, raw: { heavy: true } },
  in_service: { value: null, precision: "unknown", raw: null } });
const db = { collection(name: string) { return {
  async findOne() { reads++; if (fail) throw Error("private DB error");
    return name === "meta" ? { dataset: active } : ready ? { counts: { national_candidate_pairs: 1 } } : {}; },
  async countDocuments() { return rows.length; },
  find(filter: Record<string, unknown>) { if (name === "national_candidate_pairs") lastFilter = filter;
    let offset = 0, limit = 100;
    const cursor = { sort: () => cursor, skip: (n: number) => { offset = n; return cursor; }, limit: (n: number) => { limit = n; return cursor; }, maxTimeMS: () => cursor,
      async toArray() { return name === "national_projects" ? missingProject ? [] : [project("p1"), project("p2")]
        : rows.filter(p => !filter.id || filter.id === p.id).slice(offset, offset + limit); } }; return cursor; },
}; } };
Object.assign(globalThis, { __candidateDb: db });
registerHooks({ resolve(specifier, context, next) {
  if (specifier === "server-only") return { url: "data:text/javascript,export{}", shortCircuit: true };
  if (specifier === "@/lib/server/db") return { url: "data:text/javascript,export async function getDb(){return globalThis.__candidateDb}", shortCircuit: true };
  if (specifier.startsWith("@/")) return next(new URL(`${specifier.slice(2)}.ts`, root).href, context);
  try { return next(specifier, context); } catch (error) {
    if (specifier.startsWith(".") && !/\.[a-z]+$/i.test(specifier)) return next(`${specifier}.ts`, context);
    throw error;
  }
} });
const { GET } = await import("../../../web/app/api/national-pairs/route.ts");
const { pairFilter } = await import("../../../web/lib/national-pairs/query.ts");
const get = (query = "dataset=test:A") => GET(new Request(`http://test/api/national-pairs?${query}`));

test("dataset-pinned pages, compact summaries, scope validation and explicit failures", async () => {
  delete process.env.NATIONAL_DATA_MODE;
  let res = await get();
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("cache-control"), "no-store");
  const body = await res.json();
  assert.equal(body.total, 1); assert.equal(body.nextOffset, null);
  assert.equal(body.pairs[0].drive_mi, 3); assert.equal(body.pairs[0].route.polyline, "_p~iF~ps|U");
  assert.equal("duration_s" in body.pairs[0].route, false);
  assert.equal(body.projects.length, 2); assert.equal("raw" in body.projects[0].evidence, false);
  await get("dataset=test:A&scope=state:48"); assert.equal(lastFilter.shared_states, "48");
  await get("dataset=test:A&scope=region:3"); assert.equal(lastFilter.shared_regions, "3");
  await get("dataset=test:A&scope=plan:ercot"); assert.equal(lastFilter.shared_plans, "ercot");
  const pin = pairFilter({ dataset: "test:A", scope: "pin:30,-95", offset: 0 });
  assert.deepEqual(pin.geo_a, pin.geo_b);
  rows = Array.from({ length: 57 }, (_, i) => ({ ...candidate, id: `npc:${i.toString(16).padStart(32, "0")}`, rank: i + 1 }));
  const first = await (await get()).json();
  assert.equal(first.pairs.length, 50); assert.equal(first.nextOffset, 50); assert.equal(first.total, 57);
  const second = await (await get("dataset=test:A&offset=50")).json();
  assert.equal(second.pairs.length, 7); assert.equal(second.pairs[0].rank, 51); assert.equal(second.nextOffset, null);
  rows = [candidate];
  const before = reads;
  for (const q of ["", "dataset=x&extra=x", "dataset=x&dataset=y", "dataset=x&offset=-1", "dataset=x&scope=pin:91,0", "dataset=x&scope=state:xx", `dataset=x&id=${candidate.id}&offset=2`]) {
    assert.equal((await get(q)).status, 400);
  }
  assert.equal(reads, before);
  assert.equal((await get(`dataset=test:A&id=npc:${"b".repeat(32)}`)).status, 404);
  active = "test:B"; assert.equal((await get()).status, 409); active = "test:A";
  ready = false; assert.equal((await get()).status, 503); ready = true;
  missingProject = true; assert.equal((await get()).status, 503); missingProject = false;
  fail = true; res = await get(); assert.equal(res.status, 503); assert.doesNotMatch(await res.text(), /private DB/); fail = false;
  process.env.NATIONAL_DATA_MODE = "snapshot"; assert.equal((await get()).status, 503); delete process.env.NATIONAL_DATA_MODE;
});
