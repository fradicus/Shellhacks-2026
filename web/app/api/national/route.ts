import { parseNationalFilters } from "@/lib/national/filters";
import { loadNationalExplorer } from "@/lib/national/server";

export const dynamic = "force-dynamic";

function rawParams(req: Request): Record<string, string> | Response {
  const params = new URL(req.url).searchParams;
  const raw: Record<string, string> = {};
  for (const key of params.keys()) {
    if (params.getAll(key).length !== 1) return Response.json({ error: "invalid query", issues: [`${key}: duplicate parameter`] }, { status: 400 });
    raw[key] = params.get(key)!;
  }
  return raw;
}

export async function GET(req: Request) {
  const raw = rawParams(req);
  if (raw instanceof Response) return raw;
  try {
    const payload = await loadNationalExplorer(parseNationalFilters(raw));
    if (payload.invalidQuery) {
      return Response.json({ error: "invalid query", issues: [payload.reason] }, { status: 400, headers: { "Cache-Control": "no-store" } });
    }
    return Response.json(payload, {
      status: payload.available ? 200 : 503,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return Response.json(
      { error: "invalid query", issues: [error instanceof Error ? error.message : "invalid query"] },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
}
