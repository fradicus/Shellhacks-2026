import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtempSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { IdentityCache } from "../../../web/lib/server/cache.ts";
import { verifiedStore } from "../../../web/lib/verified/server.ts";

// Explicit test-only artifacts written to a temporary directory; nothing here enters the application.
const DATASET = "a".repeat(64);
const sha = (text: string) => createHash("sha256").update(text).digest("hex");
function publish(dir: string, names: string[], generated = "2026-09-27T00:00:00Z") {
  const utilities = JSON.stringify({ schema_version: "verified-directory-v1", dataset: DATASET, generated_at: generated,
    records: names.map((name, i) => ({ id: `test:${i}`, eia_utility_id: String(i), name, data_year: 2024, state_fips: ["13"],
      county_geoids: ["13001"], source_ids: ["test"], validation_status: "accepted", limitations: [] })) });
  const coverage = JSON.stringify({ schema_version: "verified-directory-v1", dataset: DATASET, generated_at: generated, states: [] });
  writeFileSync(join(dir, "utilities.json"), utilities);
  writeFileSync(join(dir, "coverage.json"), coverage);
  writeFileSync(join(dir, "manifest.json"), JSON.stringify({ schema_version: "verified-directory-v1", dataset: DATASET, generated_at: generated,
    files: { "utilities.json": { sha256: sha(utilities), records: names.length }, "coverage.json": { sha256: sha(coverage), records: null } } }));
}

test("identity cache: one load per identity, a new identity reloads, failures are not kept", async () => {
  const cache = new IdentityCache<number>(2);
  let loads = 0;
  const load = async () => ++loads;
  assert.equal(await cache.get("r1", load), 1);
  assert.equal(await cache.get("r1", load), 1);
  assert.equal(await cache.get("r2", load), 2);
  assert.equal(await cache.get("r3", load), 3);
  assert.equal(cache.size, 2);
  assert.equal(await cache.get("r1", load), 4, "the oldest identity aged out");
  await assert.rejects(cache.get("bad", async () => { throw new Error("transient"); }));
  assert.equal(await cache.get("bad", async () => 99), 99, "a failed load is retried, not served from cache");
});

test("verified artifacts are validated once per identity and re-read when republished", async () => {
  const dir = mkdtempSync(join(tmpdir(), "gridbridge-verified-"));
  try {
    const geography = join(dir, "geography.json");
    writeFileSync(geography, JSON.stringify({ states: [{ state_fips: "13" }], counties: [{ county_geoid: "13001", state_fips: "13" }] }));
    publish(dir, ["Test Utility A"]);
    const store = verifiedStore(dir, geography);
    const first = await store.load();
    assert.equal(await store.load(), first, "same identity: the validated directory is reused");
    assert.deepEqual(first.utilities.map((u) => u.name), ["Test Utility A"]);

    publish(dir, ["Test Utility A", "Test Utility B"]);
    const later = new Date(Date.now() + 5000);
    for (const name of ["manifest.json", "utilities.json", "coverage.json"]) utimesSync(join(dir, name), later, later);
    const second = await store.load();
    assert.notEqual(second, first);
    assert.deepEqual(second.utilities.map((u) => u.name), ["Test Utility A", "Test Utility B"]);

    writeFileSync(join(dir, "utilities.json"), "{\"tampered\": true}");
    await assert.rejects(store.load(), /manifest hash check/);
    publish(dir, ["Test Utility C"]);
    assert.deepEqual((await store.load()).utilities.map((u) => u.name), ["Test Utility C"], "a failed check is not cached");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
