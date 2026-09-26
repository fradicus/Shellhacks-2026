#!/usr/bin/env node
// Check actual Next deployment traces, not merely source-path configuration.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const verified = ["data/verified/manifest.json", "data/verified/utilities.json", "data/verified/coverage.json", "data/national/geography.json"];
const environment = ["data/environment/aef-samples.json", "data/environment/aef-samples.evidence.json", "data/environment/washington-boundary.json", "data/environment/washington-boundary.evidence.json"];
const routes = [
  ["api/verified/route", verified], ["api/verified/coverage/route", verified],
  ["api/operations/site/route", environment], ["api/operations/route/route", environment], ["api/operations/reference/route", environment],
  ["api/operations/conditions/route", environment],
  ["api/outcomes/status/route", []], ["api/outcomes/predict/route", []],
];
let checked = 0;
for (const [route, artifacts] of routes) {
  assert.ok(existsSync(path.join(root, "web/app", `${route}.ts`)), `Missing integrated API route: ${route}`);
  const tracePath = path.join(root, "web/.next/server/app", `${route}.js.nft.json`);
  assert.ok(existsSync(tracePath), `Missing deployment trace: ${route}`);
  const trace = JSON.parse(readFileSync(tracePath, "utf8"));
  const packaged = new Set(trace.files.map((file) => path.resolve(path.dirname(tracePath), file)));
  for (const file of artifacts) {
    const absolute = path.join(root, file);
    assert.ok(existsSync(absolute) && packaged.has(absolute), `${route} does not package required public evidence ${file}`);
  }
  for (const file of packaged) {
    const relative = path.relative(root, file).split(path.sep).join("/");
    assert.ok(!relative.startsWith("tests/web/outcomes/") && !relative.includes("synthetic-model.testfixture"), `${route} packages a synthetic history fixture`);
  }
  checked++;
}
console.log(`operations trace check: ${checked} available API routes package their required public evidence; no synthetic history fixture`);
