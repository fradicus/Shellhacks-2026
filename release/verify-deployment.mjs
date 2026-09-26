#!/usr/bin/env node

import { pathToFileURL } from "node:url";

const FETCH_TIMEOUT_MS = 10_000;
const MAX_HEALTH_BYTES = 128 * 1024;
const MAX_HTML_BYTES = 2 * 1024 * 1024;
const MAX_BUNDLE_BYTES = 5 * 1024 * 1024;
const MAX_BUNDLES = 64;
const MAX_REDIRECTS = 5;
const SECRET_MARKERS = ["mongodb+srv", "GEMINI", "AIza"];
const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

const usage = `Usage:
  node release/verify-deployment.mjs --commit "$COMMIT" --url "$VERCEL_URL" [--url "$DOMAIN_URL"]

Each --url must be an explicit HTTPS origin without credentials, a path, a query, or a fragment.
The command prints JSON and exits non-zero unless every supplied origin serves the expected commit,
reports an active database dataset, returns a 200 home page, exposes at least one JavaScript bundle,
and all discovered bundles pass the client-secret marker scan.`;

export function parseBaseUrl(raw) {
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("each deployment URL must be a valid absolute URL");
  }
  if (parsed.protocol !== "https:") throw new Error("each deployment URL must use HTTPS");
  if (parsed.username || parsed.password) throw new Error("deployment URLs must not contain credentials");
  if (parsed.search || parsed.hash) throw new Error("deployment URLs must not contain a query or fragment");
  if (parsed.pathname !== "/") throw new Error("each deployment URL must be an origin without a path");
  return parsed.origin;
}

export function extractScriptUrls(html, pageUrl) {
  const scripts = new Set();
  const pattern = /<script\b[^>]*\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)')[^>]*>/giu;
  for (const match of html.matchAll(pattern)) {
    const script = new URL(match[1] ?? match[2], pageUrl);
    if (script.protocol !== "https:") throw new Error("a discovered script URL does not use HTTPS");
    if (script.username || script.password) throw new Error("a discovered script URL contains credentials");
    script.hash = "";
    scripts.add(script.href);
  }
  return [...scripts];
}

export function findExposedMarkers(source) {
  return SECRET_MARKERS.filter((marker) => source.includes(marker));
}

export function validateBundleCount(count) {
  if (count === 0) throw new Error("home page exposed no JavaScript bundles to scan");
  if (count > MAX_BUNDLES) throw new Error(`home page exposed more than ${MAX_BUNDLES} JavaScript bundles`);
}

export function validateHealth(body, expectedCommit) {
  const errors = [];
  if (!body || typeof body !== "object" || Array.isArray(body)) return ["health response is not a JSON object"];
  if (body.ok !== true) errors.push("health ok is not true");
  if (body.commit !== expectedCommit) errors.push("health commit does not match the requested revision");
  if (body.db !== "up") errors.push("health database state is not up");
  if (typeof body.active_dataset !== "string" || body.active_dataset.length === 0) {
    errors.push("health has no active dataset");
  }
  return errors;
}

function parseArgs(argv) {
  const args = { urls: [], commit: null, help: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--url") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--url requires a value");
      args.urls.push(parseBaseUrl(value));
      index += 1;
    } else if (arg === "--commit") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--commit requires a value");
      args.commit = value;
      index += 1;
    } else {
      throw new Error("unknown argument; run with --help for usage");
    }
  }
  if (args.help) return args;
  if (!args.commit || !/^[0-9a-f]{40}$/iu.test(args.commit)) {
    throw new Error("--commit must be a full 40-character Git commit SHA");
  }
  if (args.urls.length === 0) throw new Error("at least one --url is required");
  args.urls = [...new Set(args.urls)];
  return args;
}

function secureTarget(value, label) {
  let target;
  try {
    target = new URL(value);
  } catch {
    throw new Error(`${label} resolved to an invalid URL`);
  }
  if (target.protocol !== "https:" || target.username || target.password) {
    throw new Error(`${label} resolved outside credential-free HTTPS`);
  }
  return target;
}

async function cancelBody(response, reader) {
  try {
    if (reader) await reader.cancel();
    else if (response?.body && !response.body.locked) await response.body.cancel();
  } catch {
    // Cancellation is best-effort; the request AbortController is also triggered on every rejection.
  }
}

async function fetchFollowingSafeRedirects(url, label, signal, fetchImpl) {
  let target = secureTarget(url, label);
  for (let redirects = 0; ; redirects += 1) {
    let response;
    try {
      response = await fetchImpl(target, {
        redirect: "manual",
        signal,
        headers: { "User-Agent": "GridBridge-release-verifier/1" },
      });
    } catch {
      throw new Error(`${label} request failed or timed out`);
    }

    if (!REDIRECT_STATUSES.has(response.status)) return { response, finalUrl: target.href };

    const location = response.headers.get("location");
    await cancelBody(response);
    if (!location) throw new Error(`${label} returned a redirect without a location`);
    if (redirects >= MAX_REDIRECTS) throw new Error(`${label} exceeded the ${MAX_REDIRECTS}-redirect limit`);
    let next;
    try {
      next = new URL(location, target);
    } catch {
      throw new Error(`${label} returned an invalid redirect location`);
    }
    target = secureTarget(next, `${label} redirect hop`);
  }
}

export async function fetchText(url, label, maxBytes, fetchImpl = fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  let response;
  let reader;
  try {
    const fetched = await fetchFollowingSafeRedirects(url, label, controller.signal, fetchImpl);
    response = fetched.response;

    const declaredLength = Number(response.headers.get("content-length"));
    if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
      throw new Error(`${label} exceeded the ${maxBytes}-byte response limit`);
    }
    if (!response.body) throw new Error(`${label} returned no response body`);

    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let bytes = 0;
    let text = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maxBytes) {
        controller.abort();
        throw new Error(`${label} exceeded the ${maxBytes}-byte response limit`);
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
    return { response, text, url: fetched.finalUrl };
  } catch (error) {
    controller.abort();
    await cancelBody(response, reader);
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function verifyOrigin(origin, expectedCommit) {
  const healthResult = await fetchText(new URL("/api/health", origin), "health", MAX_HEALTH_BYTES);
  let health;
  try {
    health = JSON.parse(healthResult.text);
  } catch {
    throw new Error("health response is not valid JSON");
  }
  if (healthResult.response.status !== 200) throw new Error(`health returned HTTP ${healthResult.response.status}`);
  const healthErrors = validateHealth(health, expectedCommit);
  if (healthErrors.length > 0) throw new Error(healthErrors.join("; "));

  const homeResult = await fetchText(new URL("/", origin), "home page", MAX_HTML_BYTES);
  if (homeResult.response.status !== 200) throw new Error(`home page returned HTTP ${homeResult.response.status}`);
  const bundles = extractScriptUrls(homeResult.text, homeResult.url);
  validateBundleCount(bundles.length);

  const exposed = new Set();
  for (let index = 0; index < bundles.length; index += 1) {
    const bundle = await fetchText(bundles[index], `bundle ${index + 1}`, MAX_BUNDLE_BYTES);
    if (bundle.response.status !== 200) throw new Error(`bundle ${index + 1} returned HTTP ${bundle.response.status}`);
    for (const marker of findExposedMarkers(bundle.text)) exposed.add(marker);
  }
  if (exposed.size > 0) throw new Error(`client bundle secret scan found: ${[...exposed].join(", ")}`);

  return {
    origin,
    https: "validated",
    root_status: homeResult.response.status,
    health_status: healthResult.response.status,
    commit: health.commit,
    db: health.db,
    active_dataset: health.active_dataset,
    bundles_scanned: bundles.length,
    secret_markers_found: [],
    ok: true,
  };
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : "invalid arguments");
    console.error(usage);
    process.exitCode = 2;
    return;
  }
  if (args.help) {
    console.log(usage);
    return;
  }

  const results = [];
  for (const origin of args.urls) {
    try {
      results.push(await verifyOrigin(origin, args.commit));
    } catch (error) {
      results.push({
        origin,
        ok: false,
        error: error instanceof Error ? error.message : "verification failed",
      });
    }
  }
  const ok = results.every((result) => result.ok);
  console.log(JSON.stringify({ checked_at: new Date().toISOString(), expected_commit: args.commit, ok, results }, null, 2));
  if (!ok) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
