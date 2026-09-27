import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import test from "node:test";

const root = new URL("../../../web/", import.meta.url);
const dataset = "search:test";
const projects = Array.from({ length: 65 }, (_, i) => ({
  dataset, id: `project:${i}`, name: i >= 60 ? "Same_Name [230 kV]" : `Project ${i}`,
  owner: i === 61 ? "Literal.* Utility" : "Filed Utility", other_owners: i === 62 ? ["Other Partner"] : [],
  native_id: `native-${i}`, source_id: i === 63 ? "source-unique" : "source-test",
  center: { lat: 30, lon: -95, basis: "one", evidence: "test only" }, states: ["48"], counties: [],
  location_review: "unreviewed", status_group: "planned", evidence: { page: 1, sheet: null, row: null, raw: {} },
  in_service: { value: null, precision: "unknown", raw: null },
}));
const rows = Array.from({ length: 64 }, (_, i) => ({ dataset, id: `npc:${i.toString(16).padStart(32, "0")}`,
  a: `project:${i}`, b: "project:64", distance_mi: 2, time_gap_days: null, band: 0, rank: i + 1,
  tier: "tentative", rule_version: "national-provisional-25mi-v1", identity_version: "test",
  shared_states: [i % 2 === 0 ? "48" : "36"],
}));
let overflow = false, searchReads = 0, pairReads = 0;
// Minimal database boundary: assertions below exercise the real API/query construction.
function matches(doc: Record<string, unknown>, filter: Record<string, unknown>): boolean {
  return Object.entries(filter).every(([field, value]) => {
    if (field === "$or") return (value as Record<string, unknown>[]).some(f => matches(doc, f));
    const values = Array.isArray(doc[field]) ? doc[field] as unknown[] : [doc[field]];
    if (value && typeof value === "object") {
      const op = value as { $in?: unknown[]; $regex?: string; $options?: string };
      if (op.$in) return values.some(v => op.$in!.includes(v));
      if (op.$regex !== undefined) return values.some(v => typeof v === "string" && new RegExp(op.$regex!, op.$options).test(v));
    }
    return values.includes(value);
  });
}
const db = { collection(name: string) { return {
  async findOne() { return name === "meta" ? { dataset } : { counts: { national_candidate_pairs: rows.length } }; },
  async countDocuments(filter: Record<string, unknown>) { return rows.filter(p => matches(p, filter)).length; },
  find(filter: Record<string, unknown>, options?: { projection?: Record<string, number> }) {
    const searching = name === "national_projects" && !!filter.$or;
    if (searching) { searchReads++; assert.deepEqual(options?.projection, { _id: 0, id: 1 }); assert.equal(filter.dataset, dataset); }
    if (name === "national_candidate_pairs") pairReads++;
    let offset = 0, limit = Infinity;
    const cursor = {
      sort: (sort: unknown) => { assert.deepEqual(sort, { rank: 1, id: 1 }); return cursor; },
      skip: (n: number) => { offset = n; return cursor; }, limit: (n: number) => { limit = n; return cursor; },
      maxTimeMS: (n: number) => { assert.equal(n, 5000); return cursor; },
      async toArray() {
        if (searching && overflow) return Array.from({ length: Math.min(limit, 10001) }, (_, i) => ({ id: String(i) }));
        const docs = name === "national_projects" ? projects : rows;
        const result = docs.filter(p => matches(p, filter)).slice(offset, offset + limit);
        return searching ? result.map(p => ({ id: p.id })) : result;
      },
    }; return cursor;
  },
}; } };
Object.assign(globalThis, { __candidateSearchDb: db });
registerHooks({ resolve(specifier, context, next) {
  if (specifier === "server-only") return { url: "data:text/javascript,export{}", shortCircuit: true };
  if (specifier === "@/lib/server/db") return { url: "data:text/javascript,export async function getDb(){return globalThis.__candidateSearchDb}", shortCircuit: true };
  if (specifier.startsWith("@/")) return next(new URL(`${specifier.slice(2)}.ts`, root).href, context);
  try { return next(specifier, context); } catch (error) {
    if (specifier.startsWith(".") && !/\.[a-z]+$/i.test(specifier)) return next(`${specifier}.ts`, context);
    throw error;
  }
} });
const { GET } = await import("../../../web/app/api/national-pairs/route.ts");
const get = (q: string, extra: Record<string, string> = {}) => GET(new Request(`http://test/api/national-pairs?${new URLSearchParams({ dataset, q, ...extra })}`));

test("search finds either endpoint across the full dataset before scope, count and paging", async () => {
  delete process.env.NATIONAL_DATA_MODE;
  const initial = await (await get("")).json();
  assert.equal(initial.pairs.length, 50); assert.equal(initial.total, 64); assert.equal(searchReads, 0);
  const exact = await (await get(" native-61 ")).json();
  assert.equal(exact.total, 1); assert.equal(exact.pairs[0].rank, 62);
  for (const q of ["literal.* utility", "Other Partner", "source-unique", "project:61"]) {
    const body = await (await get(q)).json(); assert.equal(body.total, 1, q);
  }
  assert.equal((await (await get("LiteralZZ Utility")).json()).total, 0);
  // The common B endpoint matches, so every pair survives; this includes repeated names with distinct IDs.
  const named = await (await get("same name [230 kv]")).json();
  assert.equal(named.total, 64); assert.equal(named.pairs.length, 50); assert.equal(named.nextOffset, 50);
  const second = await (await get("same_name [230 kV]", { offset: "50" })).json();
  assert.equal(second.pairs.length, 14); assert.equal(second.pairs[0].rank, 51); assert.equal(second.nextOffset, null);
  const scoped = await (await get("same name [230 kv]", { scope: "state:48" })).json();
  assert.equal(scoped.total, 32); assert(scoped.pairs.every((p: { rank: number }) => p.rank % 2 === 1));
  assert.equal((await (await get("native-61", { scope: "state:48" })).json()).total, 0);
  assert.equal((await (await get("does not exist")).json()).total, 0);
  projects[62].other_owners = []; projects[62].owner = "";
  assert.equal((await (await get("Other Partner")).json()).total, 0);
});

test("search rejects invalid input and reports overflow instead of truncating", async () => {
  const before = searchReads;
  assert.equal((await get("x".repeat(121))).status, 400);
  assert.equal((await get("project", { id: rows[0].id })).status, 400);
  const duplicate = await GET(new Request(`http://test/api/national-pairs?dataset=${dataset}&q=a&q=b`));
  assert.equal(duplicate.status, 400); assert.equal(searchReads, before);
  overflow = true;
  const reads = pairReads, res = await get("project");
  assert.equal(res.status, 422); assert.match(await res.text(), /more specific/i); assert.equal(pairReads, reads);
  overflow = false;
});
