import assert from "node:assert/strict";
import test from "node:test";
import { DbUnavailable } from "../../../web/lib/server/db.ts";
import { DeadlineExceeded } from "../../../web/lib/server/deadline.ts";
import { readFailure } from "../../../web/lib/server/http.ts";
import { MAX_LIST, repository, ResultTooLarge } from "../../../web/lib/server/repository.ts";

test("without a database the shared repository fails as unavailable, never with fixture data", async () => {
  const saved = process.env.MONGODB_URI_RO;
  delete process.env.MONGODB_URI_RO;
  try {
    await assert.rejects(repository.release(), (error: unknown) => error instanceof DbUnavailable && error.message === "database not configured");
    await assert.rejects(repository.projects({ endpoints: false }), DbUnavailable);
    await assert.rejects(repository.matchPage({ view: "historical", limit: 10, skip: 0 }), DbUnavailable);
  } finally {
    if (saved !== undefined) process.env.MONGODB_URI_RO = saved;
  }
});

test("read failures map to distinct statuses without leaking internals", () => {
  assert.deepEqual(readFailure(new DeadlineExceeded("projects", 8000)), { status: 504, reason: "database timed out" });
  assert.deepEqual(readFailure(new DbUnavailable("no active dataset loaded")), { status: 503, reason: "no active dataset loaded" });
  const tooLarge = new ResultTooLarge(`projects exceeds the ${MAX_LIST} row read bound`);
  assert.equal(readFailure(tooLarge).status, 503);
  assert.deepEqual(readFailure(new Error("mongodb+srv://user:secret@host")), { status: 503, reason: "database error" });
});

test("an aborted request cancels its read", async () => {
  const saved = process.env.MONGODB_URI_RO;
  delete process.env.MONGODB_URI_RO;
  try {
    const controller = new AbortController();
    controller.abort(new Error("client went away"));
    await assert.rejects(repository.release(controller.signal));
  } finally {
    if (saved !== undefined) process.env.MONGODB_URI_RO = saved;
  }
});
