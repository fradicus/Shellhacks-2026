import { parseNationalFilters } from "@/lib/national/filters";
import { buildMindMapTree, MIND_MAP_PROJECT_LIMIT } from "@/lib/national/mindmap";
import { loadNationalExport } from "@/lib/national/server";

export const dynamic = "force-dynamic";

function rawParams(req: Request): Record<string, string> | Response {
  const params = new URL(req.url).searchParams;
  const raw: Record<string, string> = {};
  for (const key of params.keys()) {
    if (key === "view") continue;
    if (params.getAll(key).length !== 1) {
      return Response.json({ error: "invalid query", issues: [`${key}: duplicate parameter`] }, { status: 400 });
    }
    raw[key] = params.get(key)!;
  }
  return raw;
}

export async function GET(req: Request) {
  const raw = rawParams(req);
  if (raw instanceof Response) return raw;
  try {
    const filters = parseNationalFilters(raw);
    const payload = await loadNationalExport({ ...filters, page: 1, limit: MIND_MAP_PROJECT_LIMIT });
    if (payload.invalidQuery) {
      return Response.json({ available: false, reason: payload.reason, tree: null }, { status: 400, headers: { "Cache-Control": "no-store" } });
    }
    if (!payload.available) {
      return Response.json(
        { available: false, reason: payload.reason ?? "national projects unavailable", tree: null },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      );
    }
    const tree = buildMindMapTree(payload.projects, payload.geography, { limit: MIND_MAP_PROJECT_LIMIT });
    return Response.json(
      { available: true, mode: payload.mode, dataset: payload.dataset, tree },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return Response.json(
      { available: false, reason: error instanceof Error ? error.message : "invalid mind map query", tree: null },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
}
