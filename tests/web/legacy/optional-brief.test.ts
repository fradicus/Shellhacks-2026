import assert from "node:assert/strict";
import test from "node:test";
import type { Db } from "mongodb";
import { pair } from "../../../web/lib/server/queries.ts";

function database(failure?: string, signal?: AbortSignal) {
  const rows: Record<string, object[]> = {
    matches: [{ _id: "release:pair", id: "pair", dataset: "release", a: "a", b: "b" }],
    projects: ["a", "b"].map((key) => ({ _id: `release:${key}`, id: key, dataset: "release", project_key: key, source: { source_id: "source" } })),
    sources: [{ _id: "release:source", id: "source", dataset: "release", title: "Public filing" }],
    briefs: [{ _id: "release:brief", id: "brief", dataset: "release", validation: "passed" }],
    version_changes: [], reviews: [],
  };
  const calls: { name: string; options: Record<string, unknown> }[] = [];
  const db = { collection: (name: string) => ({ find(_filter: unknown, options: Record<string, unknown>) {
    calls.push({ name, options });
    return { toArray: async () => {
      signal?.throwIfAborted();
      if (failure === name) throw new Error(`synthetic ${name} failure`);
      return rows[name] ?? [];
    } };
  } }) } as unknown as Db;
  return { db, calls };
}

test("brief-only failure preserves the pair, source records and mandatory read deadlines", async () => {
  const { db, calls } = database("briefs");
  const result = await pair(db, "release", "pair", { maxTimeMS: 1200 });
  assert.equal(result?.match._id, "pair");
  assert.equal(result?.a?._id, "a");
  assert.equal(result?.b?._id, "b");
  assert.equal(result?.sources?.[0]._id, "source");
  assert.equal(result?.brief, null);
  assert.ok(calls.every((call) => call.options.maxTimeMS === 1200));
});

test("healthy stored brief is retained", async () => {
  assert.equal((await pair(database().db, "release", "pair"))?.brief?._id, "brief");
});

test("mandatory match, project, source, review and version reads continue to fail closed", async () => {
  for (const name of ["matches", "projects", "sources", "reviews", "version_changes"]) {
    await assert.rejects(pair(database(name).db, "release", "pair"), new RegExp(`synthetic ${name} failure`));
  }
});

test("caller cancellation is not converted into an optional-brief success", async () => {
  const controller = new AbortController();
  const { db } = database("briefs");
  const work = pair(db, "release", "pair", { signal: controller.signal });
  controller.abort(new Error("caller cancelled"));
  await assert.rejects(work, /caller cancelled/);
});
