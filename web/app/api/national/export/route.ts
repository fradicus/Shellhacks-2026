import { parseNationalFilters } from "@/lib/national/filters";
import { loadNationalExport } from "@/lib/national/server";
import { toCsv } from "@/app/api/export/csv";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const raw: Record<string, string> = {};
  for (const key of params.keys()) {
    if (params.getAll(key).length !== 1) return Response.json({ error: "invalid query", issues: [`${key}: duplicate parameter`] }, { status: 400 });
    raw[key] = params.get(key)!;
  }
  try {
    const format = raw.format ?? "csv";
    if (format !== "csv" && format !== "json") throw new Error("format: must be csv or json");
    delete raw.format;
    const payload = await loadNationalExport(parseNationalFilters(raw));
    if (!payload.available) {
      const status = payload.invalidQuery ? 400 : payload.reason?.startsWith("Export is limited") ? 413 : 503;
      return Response.json(payload.invalidQuery ? { error: "invalid query", issues: [payload.reason] } : { unavailable: true, reason: payload.reason }, { status });
    }
    if (format === "json") return Response.json({
      dataset: payload.dataset, mode: payload.mode, filters: payload.filters,
      total: payload.total, locatedTotal: payload.locatedTotal, unlocatedTotal: payload.unlocatedTotal,
      projects: payload.projects, sources: payload.sources, coverage: payload.coverage,
    }, { headers: {
      "Cache-Control": "no-store",
      "Content-Disposition": 'attachment; filename="gridbridge-national-projects.json"',
    } });
    const header = ["id", "name", "owner", "planning_region", "states", "counties", "status", "in_service_raw", "in_service_value", "in_service_precision", "location_review", "latitude", "longitude", "source_id", "source_page", "source_sheet", "source_row"];
    const rows = payload.projects.map((project) => [
      project._id, project.name, project.owner, project.planning_region, project.states.join("|"), project.counties.join("|"),
      project.status ?? project.status_group, project.in_service.raw, project.in_service.value, project.in_service.precision,
      project.location_review, project.center?.lat, project.center?.lon, project.source_id, project.evidence.page,
      project.evidence.sheet, project.evidence.row,
    ]);
    const csv = toCsv(header, rows);
    return new Response(csv, {
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="gridbridge-national-projects.csv"',
      },
    });
  } catch (error) {
    return Response.json({ error: "invalid query", issues: [error instanceof Error ? error.message : "invalid query"] }, { status: 400 });
  }
}
