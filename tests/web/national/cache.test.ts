import assert from "node:assert/strict";
import { registerHooks } from "node:module";
import { fileURLToPath } from "node:url";
import test from "node:test";

// Exercise the production loader; only its DB boundary and server-only marker are replaced.
const root = new URL("../../../web/", import.meta.url);
process.chdir(fileURLToPath(root));
delete process.env.NATIONAL_DATA_MODE;
let active: string | null = "test:A";
let pointerFails = false;
let queryFails = false;
let invalidRecord = false;
let reads = 0;
let pointers = 0;
const blocked = new Map<string, Promise<void>>();
const fixtureProject = (dataset: string) => ({
  id: `${dataset}:project`, dataset, name: "Explicit cache test fixture", source_id: "test:source",
  states: ["48"], counties: ["48001"], status_group: "planned", location_review: "unreviewed",
  center: { lat: invalidRecord ? 999 : 31, lon: -95 },
  in_service: { value: "2030", precision: "year", raw: "2030" }, evidence: { raw: { fixture: true } },
});
const db = {
  collection(name: string) {
    async function read(filter: unknown, rows: boolean) {
      reads++;
      const dataset = JSON.stringify(filter).match(/"dataset":"([^"]+)"/)?.[1] ?? "missing";
      await blocked.get(dataset);
      if (queryFails) throw new Error("test-only query failure");
      if (name === "national_runs") return null;
      if (!rows) return JSON.stringify(filter).includes("approximate_location") ? 0 : 1;
      if (name === "national_sources") return [{ id: "test:source", title: "Fixture", publisher: "Test", states: ["48"], notes: [] }];
      return [fixtureProject(dataset)];
    }
    return {
      async findOne(filter: unknown) {
        if (name !== "meta") return read(filter, false);
        pointers++;
        if (pointerFails) throw new Error("test-only pointer failure");
        return active ? { dataset: active } : null;
      },
      countDocuments: (filter: unknown) => read(filter, false),
      find(filter: unknown) {
        const cursor = { sort: () => cursor, skip: () => cursor, limit: () => cursor,
          maxTimeMS: () => cursor, toArray: () => read(filter, true) };
        return cursor;
      },
      aggregate() {
        const cursor = { maxTimeMS: () => cursor, async toArray() { reads++; return []; } };
        return cursor;
      },
    };
  },
};
Object.assign(globalThis, { __nationalCacheTestDb: db });
registerHooks({ resolve(specifier, context, next) {
  if (specifier === "server-only") return { url: "data:text/javascript,export{}", shortCircuit: true };
  if (specifier === "@/lib/server/db") return {
    url: "data:text/javascript,export async function getDb(){return globalThis.__nationalCacheTestDb}", shortCircuit: true,
  };
  try { return next(specifier, context); }
  catch (error) {
    if (specifier.startsWith(".") && !/\.[a-z]+$/i.test(specifier)) return next(`${specifier}.ts`, context);
    throw error;
  }
} });
const { loadNationalExplorer } = await import("../../../web/lib/national/server.ts");
const map = () => loadNationalExplorer({ page: 1, limit: 1 });
const nextFill = async () => {
  const before = reads;
  const result = await map();
  assert.equal(result.available, true);
  assert.equal(reads - before, 10, "one fill does the existing ten data/count/facet reads");
  return result;
};

// Sequential scenarios share a warm server module, just like repeated requests.
test("map cache preserves results, dataset freshness, isolation and retry", { timeout: 10_000 }, async () => {
  const first = await nextFill();
  const before = reads;
  assert.deepEqual(await map(), first);
  assert.equal(reads, before);
  assert.equal(pointers, 2, "active pointer still checked on a warm hit");

  active = "test:B";
  const second = await nextFill();
  assert.equal(second.dataset, active);
  assert.equal(second.mapProjects[0]._id, "test:B:project");
  active = "test:A";
  assert.deepEqual(await nextFill(), first, "rollback reloads the selected dataset");

  const warmReads = reads;
  for (const filters of [{ page: 1, limit: 2 }, { page: 2, limit: 1 }, { page: 1, limit: 1, owner: "Test" }]) {
    await loadNationalExplorer(filters);
    await loadNationalExplorer(filters);
  }
  assert.equal(reads - warmReads, 60, "other queries never reuse the map result");

  pointerFails = true;
  assert.equal((await map()).available, false, "no old-cache fallback on pointer failure");
  pointerFails = false;
  active = null;
  assert.equal((await map()).available, false);

  active = "test:retry";
  queryFails = true;
  assert.equal((await map()).available, false);
  queryFails = false;
  await nextFill();

  active = "test:invalid";
  invalidRecord = true;
  assert.equal((await map()).available, false);
  invalidRecord = false;
  await nextFill();

  const now = Date.now;
  try {
    Date.now = () => now() + 5 * 60_000 + 1;
    await nextFill();
  } finally { Date.now = now; }

  active = "test:concurrent";
  let release!: () => void;
  blocked.set(active, new Promise<void>((resolve) => { release = resolve; }));
  const beforeConcurrent = reads;
  const beforePointers = pointers;
  const a = map();
  const b = map();
  // Both calls first read the public reference files asynchronously.
  while (pointers < beforePointers + 2 || reads === beforeConcurrent) await new Promise((resolve) => setTimeout(resolve, 1));
  release();
  const [one, two] = await Promise.all([a, b]);
  assert.deepEqual(one, two);
  assert.equal(reads - beforeConcurrent, 10);
  blocked.clear();

  active = "test:old-failure";
  let reject!: (error: Error) => void;
  blocked.set(active, new Promise<void>((_resolve, fail) => { reject = fail; }));
  const previousReads = reads;
  const old = map();
  while (reads === previousReads) await new Promise((resolve) => setTimeout(resolve, 1));
  active = "test:new-success";
  const newer = await nextFill();
  reject(new Error("test-only late failure"));
  assert.equal((await old).available, false);
  const afterNew = reads;
  assert.deepEqual(await map(), newer);
  assert.equal(reads, afterNew, "late failure does not evict the new entry");

  process.env.NATIONAL_DATA_MODE = "snapshot";
  process.env.VERCEL_ENV = "production";
  assert.equal((await map()).available, false, "production never falls back to snapshots or cached Atlas");
  process.env.VERCEL_ENV = "preview";
  const snapshot = await map();
  assert.equal(snapshot.mode, "snapshot");
  assert.equal(snapshot.available, true);
  assert.equal(reads, afterNew, "snapshot mode bypasses Atlas/cache");
  delete process.env.NATIONAL_DATA_MODE;
  delete process.env.VERCEL_ENV;
});
