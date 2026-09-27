import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { DeadlineExceeded, withDeadline } from "../../../web/lib/server/deadline.ts";

// The national reader resolves `data/national` from the web app's working directory, as `next` runs it.
process.chdir(fileURLToPath(new URL("../../../web/", import.meta.url)));
process.env.NATIONAL_DATA_MODE = "snapshot";
delete process.env.VERCEL_ENV;
const { loadNationalExplorer, loadNationalRecords } = await import("../../../web/lib/national/server.ts");
const { parseNationalFilters } = await import("../../../web/lib/national/filters.ts");

test("snapshot facets and records are computed once per snapshot identity and reused", async () => {
  const first = await loadNationalExplorer(parseNationalFilters({}));
  const again = await loadNationalExplorer(parseNationalFilters({ page: "2" }));
  assert.equal(first.available, true, first.reason ?? "");
  assert.equal(first.mode, "snapshot");
  assert.equal(again.facets, first.facets, "facets come from the cached snapshot, not a recomputation");
  assert.equal(again.dataset, first.dataset);
});

test("History reads every filtered record, located or not, without the raw source row", async () => {
  const explorer = await loadNationalExplorer(parseNationalFilters({}));
  const records = await loadNationalRecords();
  assert.equal(records.available, true, records.reason ?? "");
  assert.equal(records.total, explorer.total);
  assert.equal(records.projects.length, Math.min(records.total, 10_000));
  assert.equal(records.truncated, records.total > records.projects.length);
  assert.ok(records.projects.some((p) => p.center === null), "unlocated records are part of the history dataset");
  assert.ok(records.projects.every((p) => !("raw" in p.evidence)));
});

test("a total deadline aborts the work and names what timed out", async () => {
  let aborted = false;
  await assert.rejects(
    withDeadline("test read", 20, (signal) => new Promise((resolve) => {
      signal.addEventListener("abort", () => { aborted = true; });
      setTimeout(resolve, 500);
    })),
    (error: unknown) => error instanceof DeadlineExceeded && /test read/.test(error.message),
  );
  assert.equal(aborted, true);
  const parent = new AbortController();
  const pending = withDeadline("cancelled read", 1000, () => new Promise(() => {}), parent.signal);
  parent.abort();
  await assert.rejects(pending);
  assert.equal(await withDeadline("fast read", 1000, async () => 42), 42);
});
