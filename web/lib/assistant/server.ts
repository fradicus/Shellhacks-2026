import "server-only";
import type { NationalSummaryPayload } from "../national/types";
import { validateAssistantAction, type AssistantContext } from "./commands";
import { AssistantRequestSchema, ModelDecisionSchema, type AssistantRequest, type AssistantResponse, type ModelDecision } from "./contracts";
import { assistantStatus, configured, generateDecision, readBoundedJson, type GeminiConfig } from "./provider";

export type AssistantDeps = {
  env?: NodeJS.ProcessEnv;
  load?: (filters: AssistantRequest["filters"]) => Promise<NationalSummaryPayload>;
  generate?: (config: GeminiConfig, input: unknown) => Promise<ModelDecision>;
  now?: () => number;
  bodyTimeoutMs?: number;
};
const headers = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
const json = (value: unknown, status = 200) => Response.json(value, { status, headers });
const fail = (requestId: string, message: string, dataset: string | null = null): AssistantResponse => ({ status: "unavailable", message, requestId, dataset, action: null, model: null, provider: null });
const folded = (value: string) => value.normalize("NFKC").toLocaleLowerCase("en-US");
const mentions = (message: string, name: string) => new RegExp(`(?:^|[^a-z0-9])${folded(name).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?:$|[^a-z0-9])`).test(folded(message));

function authoritativeContext(data: NationalSummaryPayload, request: AssistantRequest): AssistantContext {
  const ids = new Set([...data.projects, ...data.mapProjects].map((p) => p._id));
  return { states: data.geography?.states ?? [], counties: data.geography?.counties ?? [], regions: data.geography?.regions ?? [], planningRegions: data.facets.planningRegions, owners: data.facets.owners, visibleProjectIds: request.visibleProjectIds.filter((id) => ids.has(id)) };
}
function requestedState(request: AssistantRequest, context: AssistantContext): string | null | undefined {
  const message = folded(request.message);
  const qualified = context.states.filter((s) => mentions(message, s.name) ||
    // Postal codes must be qualifiers, not arbitrary prose tokens such as "in", "or", or "me".
    new RegExp(`(?:,\\s*|\\bin\\s+)${s.usps}\\b`, "i").test(request.message));
  return qualified.length === 1 ? qualified[0].state_fips : qualified.length === 0 ? request.filters.state : null;
}
function ambiguousCounty(request: AssistantRequest, context: AssistantContext): boolean {
  const mentioned = context.counties.filter((c) => mentions(request.message, c.full_name) || mentions(request.message, c.name));
  const groups = new Map<string, Set<string>>();
  for (const county of mentioned) { const key = folded(county.name); const states = groups.get(key) ?? new Set<string>(); states.add(county.state_fips); groups.set(key, states); }
  const ambiguous = [...groups.values()].filter((states) => states.size > 1);
  if (!ambiguous.length) return false;
  const state = requestedState(request, context);
  return !state || ambiguous.some((states) => !states.has(state));
}
function modelInput(data: NationalSummaryPayload, request: AssistantRequest, context: AssistantContext) {
  const ids = new Set(context.visibleProjectIds);
  const projects = [...new Map([...data.projects, ...data.mapProjects].filter((p) => ids.has(p._id)).map((p) => [p._id, p])).values()];
  const message = folded(request.message);
  const counties = context.counties.filter((c) => message.includes(folded(c.name)) || c.state_fips === request.filters.state).slice(0, 100);
  return { request: request.message, filters: request.filters, dataset: data.dataset, available: data.available,
    // Deliberately omit source descriptions, raw rows, URLs and all Georgia document text.
    untrusted_catalog: { states: context.states, regions: context.regions, counties, counties_truncated: counties.length < context.counties.length, planningRegions: context.planningRegions.slice(0, 100), owners: context.owners.slice(0, 200), projects: projects.map((p) => ({ id: p._id, name: p.name.slice(0, 160), states: p.states, counties: p.counties, status: p.status_group })) } };
}
function help(topic: string, data: NationalSummaryPayload): string {
  switch (topic) {
    case "data_coverage": return data.available
      ? `The current filtered dataset contains ${data.total} projects: ${data.locatedTotal} with located centers, ${data.approximateTotal ?? "an unknown count"} with approximate geography, and ${data.unlocatedTotal} unlocated. These are filtered dataset counts, not nationwide completeness. ${data.sources.filter((s) => s.import_status === "imported").length} sources are marked imported in its source catalog. Inspect Coverage and each project's evidence for scope.`
      : "Project data is currently unavailable. Coverage counts are unknown; no zero-project claim can be made.";
    case "overlap_rules": return "The current overlap rule requires a stored, verified fastest driving route of 25 miles or less (inclusive), bound to the eligible project centers. Straight-line distance is only a candidate prefilter. A missing or unverified route is not a confirmed overlap. An overlap remains a coordination lead, not proof of shared construction or savings.";
    case "source_quality": return "Project facts retain their source and location review. A source-listed state or a county reference does not establish a precise worksite. Unreviewed, approximate and unavailable locations remain distinct. Inspect the selected project's evidence before planning work.";
    case "construction_dates": return "Filed in-service milestones are not construction start dates. Original day, month, year or unknown precision is preserved. A date change records a changed filing, not necessarily delayed construction. Use History to inspect source-linked observations.";
    case "weather_routes": return "Operations provides separately sourced weather, roadwork, soil and annual satellite context with timestamps and coverage limitations. Truck routing requires provisioned access and complete vehicle facts. Missing roadwork reports do not prove a clear road; annual satellite evidence is not live weather or a soil-strength assessment.";
    default: return "I can change supported project filters, focus reference geography, select a currently visible project, navigate approved app views, and explain coverage, source quality, dates, overlaps and operations. I cannot edit records, run code, promise savings or invent project facts.";
  }
}

/** Limits are shared by this process, not by spoofable client IP headers. No cache or durable writes. */
export function createAssistantHandlers(deps: AssistantDeps = {}) {
  let active = 0; let windowStart = 0; let requests = 0;
  const now = deps.now ?? Date.now;
  const load = deps.load ?? (async (filters) => (await import("../national/server")).loadNationalSummaries(filters));
  const generate = deps.generate ?? generateDecision;
  return {
    GET: async (request: Request) => new URL(request.url).search ? json({ error: "Unsupported query" }, 400) : json(assistantStatus(deps.env)),
    POST: async (request: Request) => {
      let requestId = "unknown";
      let dataset: string | null = null;
      const origin = request.headers.get("origin");
      const url = new URL(request.url);
      if (url.search || origin !== url.origin || (request.headers.get("sec-fetch-site") && request.headers.get("sec-fetch-site") !== "same-origin")) return json(fail(requestId, "Same-origin requests are required."), 403);
      if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers.get("content-type") ?? "")) return json(fail(requestId, "A JSON request is required."), 415);
      const stamp = now(); if (stamp - windowStart >= 60000) { requests = 0; windowStart = stamp; }
      if (active >= 2 || requests >= 10) return json(fail(requestId, "Assistant request limit reached. Please try again shortly."), 429);
      requests++; active++;
      try {
        const length = request.headers.get("content-length");
        if (length && (!/^\d+$/.test(length) || Number(length) > 32768)) return json(fail(requestId, "Request body exceeds the limit."), 413);
        const abort = new AbortController(); const timer = setTimeout(() => abort.abort(), deps.bodyTimeoutMs ?? 2000);
        let input: AssistantRequest;
        try { input = AssistantRequestSchema.parse(await readBoundedJson(request.body, 32768, abort.signal)); }
        catch { return json(fail(requestId, "Invalid or oversized assistant request."), 400); }
        finally { clearTimeout(timer); abort.abort(); }
        requestId = input.requestId;
        dataset = input.dataset;
        const config = configured(deps.env);
        if (!config) return json(fail(requestId, assistantStatus(deps.env).reason!, dataset), 503);
        let contextTimer: ReturnType<typeof setTimeout> | undefined;
        let data: NationalSummaryPayload;
        try { data = await Promise.race([load(input.filters), new Promise<never>((_, reject) => { contextTimer = setTimeout(() => reject(new Error("Context deadline")), 10000); })]); }
        finally { clearTimeout(contextTimer); }
        if (dataset !== null && dataset !== data.dataset) return json(fail(requestId, "The published dataset changed. Refresh before asking the assistant again.", dataset), 409);
        const context = authoritativeContext(data, input);
        if (ambiguousCounty(input, context)) return json({ ...fail(requestId, "Which state do you mean for that county?", dataset), status: "clarification" });
        const decision = ModelDecisionSchema.parse(await generate(config, modelInput(data, input, context)));
        const base = { requestId, dataset, model: config.model, provider: "gemini" as const, action: null };
        if (decision.kind === "help") return json({ ...base, status: "answer", message: help(decision.topic, data) });
        // A model clarification is a signal, not a channel for unchecked factual assertions or links.
        if (decision.kind === "clarification") return json({ ...base, status: "clarification", message: "Please specify the state, project, filter, or app view you mean." });
        if (decision.kind === "unsupported") return json({ ...base, status: "unsupported", message: "That request is outside the assistant's supported app controls and help topics." });
        try {
          if (!data.available && !["navigate", "filters.reset"].includes(decision.action.type)) throw new Error("Unavailable context");
          const action = validateAssistantAction(decision.action, context);
          const countyId = action.type === "filters.patch" ? action.filters.county : action.type === "geography.focus" && action.kind === "county" ? action.code : undefined;
          const county = context.counties.find((c) => c.county_geoid === countyId);
          if (county && context.counties.filter((c) => folded(c.name) === folded(county.name)).length > 1
            && (mentions(input.message, county.name) || mentions(input.message, county.full_name))
            && requestedState(input, context) !== county.state_fips) throw new Error("County state differs from request");
          return json({ ...base, status: "action", action, message: "Validated one app action. You can undo or reset its effect." });
        } catch { return json({ ...base, status: "unsupported", message: "That action does not match the current app catalog or visible results. Refresh or clarify the request." }); }
      } catch { return json(fail(requestId, "The assistant is temporarily unavailable. Manual app controls still work.", dataset), 503); }
      finally { active--; }
    },
  };
}
