import assert from "node:assert/strict";
import test from "node:test";

import {
  extractScriptUrls,
  fetchText,
  findExposedMarkers,
  parseBaseUrl,
  validateBundleCount,
  validateHealth,
} from "./verify-deployment.mjs";

test("deployment origins must be explicit credential-free HTTPS origins", () => {
  assert.equal(parseBaseUrl("https://gridbridge.example/"), "https://gridbridge.example");
  for (const value of [
    "http://gridbridge.example",
    "https://user:pass@gridbridge.example",
    "https://gridbridge.example/path",
    "https://gridbridge.example/?token=hidden",
    "not-a-url",
  ]) {
    assert.throws(() => parseBaseUrl(value));
  }
});

test("every redirect hop must remain credential-free HTTPS", async () => {
  const calls = [];
  const fakeFetch = async (url, options) => {
    calls.push({ url: url.href, redirect: options.redirect });
    return new Response(null, { status: 302, headers: { location: "http://downgrade.example/then-back" } });
  };
  await assert.rejects(
    fetchText(new URL("https://gridbridge.example/"), "home page", 1024, fakeFetch),
    /redirect hop resolved outside credential-free HTTPS/,
  );
  assert.deepEqual(calls, [{ url: "https://gridbridge.example/", redirect: "manual" }]);
});

test("an oversized declared response is aborted and its body is cancelled", async () => {
  let cancelled = false;
  let signal;
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode("not read"));
    },
    cancel() {
      cancelled = true;
    },
  });
  const fakeFetch = async (_url, options) => {
    signal = options.signal;
    return new Response(body, { status: 200, headers: { "content-length": "2048" } });
  };
  await assert.rejects(
    fetchText(new URL("https://gridbridge.example/large.js"), "bundle 1", 1024, fakeFetch),
    /exceeded the 1024-byte response limit/,
  );
  assert.equal(cancelled, true);
  assert.equal(signal.aborted, true);
});

test("script discovery resolves and deduplicates HTTPS bundle URLs", () => {
  const html = `
    <script src="/_next/static/a.js"></script>
    <script async src='https://cdn.example/b.js?v=1'></script>
    <script src="/_next/static/a.js"></script>`;
  assert.deepEqual(extractScriptUrls(html, "https://gridbridge.example/"), [
    "https://gridbridge.example/_next/static/a.js",
    "https://cdn.example/b.js?v=1",
  ]);
  assert.throws(() => extractScriptUrls('<script src="http://cdn.example/a.js"></script>', "https://gridbridge.example/"));
  assert.throws(() => extractScriptUrls('<script src="https://user:pass@cdn.example/a.js"></script>', "https://gridbridge.example/"));
});

test("client secret marker scan checks every required literal", () => {
  assert.deepEqual(findExposedMarkers("mongodb+srv://redacted GEMINI_API_KEY AIza-test"), [
    "mongodb+srv",
    "GEMINI",
    "AIza",
  ]);
  assert.deepEqual(findExposedMarkers("ordinary client bundle"), []);
});

test("an absent or incomplete bundle scan cannot pass", () => {
  assert.throws(() => validateBundleCount(0), /no JavaScript bundles/);
  assert.doesNotThrow(() => validateBundleCount(1));
  assert.throws(() => validateBundleCount(65), /more than 64/);
});

test("health validation requires the exact commit and an active database dataset", () => {
  const commit = "a".repeat(40);
  assert.deepEqual(validateHealth({ ok: true, commit, db: "up", active_dataset: "dataset-sha" }, commit), []);
  assert.deepEqual(
    validateHealth({ ok: false, commit: "b".repeat(40), db: "up", active_dataset: null }, commit),
    ["health ok is not true", "health commit does not match the requested revision", "health has no active dataset"],
  );
});
