#!/usr/bin/env node
// A build must package the server-only national files needed after deployment.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const files = ["geography.json", "sources.json", "projects.json", "coverage.json"];
if (!existsSync(path.join(root, "web/app/explore/page.tsx")) || !existsSync(path.join(root, "data/national/projects.json"))) {
  console.log("national trace check: deferred until the F30 snapshot and F31 route are present");
  process.exit(0);
}
const routes = [
  "explore/page", "api/national/reference/route", "api/national/route", "api/national/export/route",
];
if (existsSync(path.join(root, "web/app/assistant/page.tsx"))) routes.push("assistant/page");
if (existsSync(path.join(root, "web/app/api/assistant/route.ts"))) routes.push("api/assistant/route");
for (const route of routes) {
  const traceFile = path.join(root, "web/.next/server/app", `${route}.js.nft.json`);
  assert.ok(existsSync(traceFile), `missing server trace for ${route}`);
  const trace = JSON.parse(readFileSync(traceFile, "utf8"));
  const packaged = new Set(trace.files.map((file) => path.resolve(path.dirname(traceFile), file)));
  for (const name of files) {
    const target = path.join(root, "data/national", name);
    assert.ok(existsSync(target), `missing published national file: ${name}`);
    assert.ok(packaged.has(target), `${route} does not package ${name}`);
  }
}
console.log(`national trace check: ${routes.length} server routes package all 4 required national JSON files`);
