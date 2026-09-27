import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import test from "node:test";
import ts from "../../../web/node_modules/typescript/lib/typescript.js";
import { createElement } from "../../../web/node_modules/react/index.js";
import { renderToStaticMarkup } from "../../../web/node_modules/react-dom/server.node.js";
import type { LocationVerification } from "../../../web/lib/national/types.ts";

// Exercise the actual route without a database; only the data loader is replaced.
const fixtureGlobal = globalThis as typeof globalThis & { nationalExportTestPayload?: unknown };
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === "@/lib/national/server") return {
      url: "data:text/javascript,export async function loadNationalExport() { return globalThis.nationalExportTestPayload; }",
      shortCircuit: true,
    };
    if (specifier.startsWith("@/")) return next(new URL(`../../../web/${specifier.slice(2)}.ts`, import.meta.url).href, context);
    if (specifier.endsWith("/locations")) return next(`${specifier}.ts`, context);
    return next(specifier, context);
  },
  load(url, context, next) {
    if (url.endsWith(".tsx")) return {
      format: "module", shortCircuit: true,
      source: ts.transpileModule(readFileSync(new URL(url), "utf8"), {
        compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX },
      }).outputText,
    };
    return next(url, context);
  },
});
const { GET } = await import("../../../web/app/api/national/export/route.ts");
const { LocationEvidence } = await import("../../../web/components/national/LocationEvidence.tsx");
const { LocationSummary } = await import("../../../web/components/national/LocationSummary.tsx");
const source = {
  publisher: "Test publisher", url: "https://example.org/test-only", artifact_sha256: "a".repeat(64),
  locator: "Test row 2", source_date: null, retrieved_at: "2026-09-27T00:00:00Z", access_review: "Test only", facts: "Test identity evidence",
};
const verification: LocationVerification = {
  project_id: "test-only:site", project_facts_sha256: "b".repeat(64), producer: "test-producer", location_kind: "site",
  points: [{
    role: "site", facility_id: "test-facility", facility_name: "Test station", lat: 43, lon: -72,
    original_geometry: { crs: "EPSG:4326", type: "Point", coordinates: [-72, 43], transform: "Test identity" },
    precision: null, uncertainty_m: null, geometry_evidence: [source], identity_evidence: [source], identity_rationale: "Test rationale",
  }],
  reviews: [
    { id: "old", reviewer: "test-reviewer", reviewed_at: "2026-09-26T00:00:00Z", decision: "insufficient", facts_sha256: "c".repeat(64), reason: "Old test decision" },
    { id: "new", reviewer: "test-reviewer", reviewed_at: "2026-09-27T00:00:00Z", decision: "confirmed", facts_sha256: "d".repeat(64), reason: "Latest test decision" },
  ], events: [],
};

test("location evidence retains unknowns, clickable citations, latest review and site/endpoint meaning", () => {
  const render = (value: LocationVerification) => renderToStaticMarkup(createElement(LocationEvidence, { verification: value }));
  const site = render(verification);
  assert.match(site, /Substation site point/);
  assert.match(site, /Precision: Not reported/);
  assert.match(site, /Source date: Not reported/);
  assert.match(site, /href="https:\/\/example.org\/test-only"/);
  assert.match(site, /Latest test decision/);
  assert.doesNotMatch(site, /Old test decision/);
  assert.match(site, /Location confirmation is separate from construction status/);
  const partial = { ...verification, location_kind: "line" as const, points: [{ ...verification.points[0], role: "a" as const }] };
  assert.match(render(partial), /Partial endpoint coverage/);
  assert.match(render({ ...partial, points: [...partial.points, { ...partial.points[0], role: "b" }] }), /Complete endpoint coverage/);
});

test("county details and CSV retain precision, attribution and null exact coordinates", async () => {
  const texas = JSON.parse(readFileSync(new URL("../../../data/texas/statewide/projects.json", import.meta.url), "utf8"));
  const county = texas.find((p: { approximate_location?: unknown }) => p.approximate_location);
  const candidate = texas.find((p: { location_candidate?: unknown }) => p.location_candidate);
  const details = renderToStaticMarkup(createElement(LocationSummary, { project: county }));
  assert.match(details, /Approximate location — county only/);
  assert.match(details, /Census reference geography/);
  assert.match(renderToStaticMarkup(createElement(LocationSummary, { project: candidate })), /not independently reviewed/);
  assert.match(renderToStaticMarkup(createElement(LocationSummary, { project: candidate })), /OpenStreetMap contributors/);
  fixtureGlobal.nationalExportTestPayload = {
    available: true, projects: [county, candidate], sources: [], total: 2, locatedTotal: 1,
    approximateTotal: 1, unlocatedTotal: 0,
  };
  try {
    const csv = await (await GET(new Request("https://example.org/api/national/export"))).text();
    assert.match(csv, /approximate_location,candidate_evidence/);
    assert.match(csv, /eligible_for_matching/);
    assert.match(csv, /ODbL/);
    const json = await (await GET(new Request("https://example.org/api/national/export?format=json"))).json();
    assert.equal(json.projects[0].center, null);
    assert.deepEqual(json.projects[0].approximate_location, county.approximate_location);
  } finally { delete fixtureGlobal.nationalExportTestPayload; }
});

test("actual export route preserves embedded evidence and dataset while retaining CSV and strict query handling", async () => {
  const project = {
    _id: "test-only:site", name: "Test site", owner: null, planning_region: "test", states: ["50"], counties: [],
    status_group: "planned", in_service: { raw: "2027", value: "2027", precision: "year" },
    center: { lat: 43, lon: -72 }, location_review: "confirmed", source_id: "test-source",
    evidence: { page: null, sheet: "Test", row: 2 }, location_verification: verification,
  };
  fixtureGlobal.nationalExportTestPayload = {
    available: true, dataset: "test-only-dataset", mode: "atlas", filters: {}, total: 1, locatedTotal: 1, unlocatedTotal: 0,
    projects: [project], sources: [source], coverage: { testOnly: true },
  };
  const get = (query: string) => GET(new Request(`https://example.org/api/national/export${query}`));
  try {
    const json = await get("?format=json");
    assert.equal(json.status, 200);
    assert.equal(json.headers.get("Cache-Control"), "no-store");
    const exported = await json.json();
    assert.equal(exported.dataset, "test-only-dataset");
    assert.deepEqual(exported.projects[0].location_verification, verification);
    const csv = await get("");
    assert.match(csv.headers.get("Content-Type") ?? "", /^text\/csv/);
    assert.equal(await (await get("?format=csv")).text(), await csv.text());
    for (const query of ["?format=xml", "?format=", "?format=json&format=csv", "?format=json&unexpected=1"]) {
      assert.equal((await get(query)).status, 400, query);
    }
    fixtureGlobal.nationalExportTestPayload = { available: false, reason: "Export is limited to 2,000 filtered records." };
    assert.equal((await get("?format=json")).status, 413);
    fixtureGlobal.nationalExportTestPayload = { available: false, reason: "national database unavailable" };
    assert.equal((await get("?format=json")).status, 503);
  } finally {
    delete fixtureGlobal.nationalExportTestPayload;
  }
});
