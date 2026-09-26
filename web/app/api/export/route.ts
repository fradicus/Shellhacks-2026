import { z } from "zod";
import { getMatches, getProjects, isFixtureMode } from "@/lib/data";
import { activeDataset, getDb } from "@/lib/server/db";
import * as q from "@/lib/server/queries";
import { isUnavailable, type MatchRow, type Project } from "@/lib/types";
import { toCsv, type Cell } from "./csv";

export const dynamic = "force-dynamic";

const MAX_ROWS = 5000;
const Query = z.strictObject({
  type: z.enum(["matches", "projects"]),
  view: z.enum(["future", "historical", "tentative"]).optional(),
});

const side = (p: Project | null, key: string): Cell[] => [
  key,
  p?.utility,
  p?.name,
  p?.in_service.raw,
  p?.in_service.date,
  p?.in_service.precision,
  p?.location_confidence ?? "needs review",
  p?.center?.basis ?? "no center",
  p?.source.source_id,
  p?.source.page,
];
const sideHeader = (x: string) =>
  ["key", "utility", "name", "in_service_raw", "in_service_date", "in_service_precision", "location_confidence", "center_basis", "source_id", "source_page"].map(
    (h) => `${x}_${h}`,
  );

function matchesCsv(rows: MatchRow[]): string {
  return toCsv(
    ["rank", "pair_id", "view", "band", "distance_mi", "distance_mi_2dp", "time_gap_days", "review_state",
      ...sideHeader("a"), ...sideHeader("b"), "rule_version", "rank_version", "analysis_date"],
    rows.map((m) => [
      m.rank, m._id, m.view, m.band === 0 ? "<10 mi" : "10-25 mi", m.distance_mi, m.distance_mi.toFixed(2),
      m.time_gap_days ?? "unknown", m.review_state ?? "needs_review",
      ...side(m.project_a, m.a), ...side(m.project_b, m.b), m.rule_version, m.rank_version, m.analysis_date,
    ]),
  );
}

function projectsCsv(rows: Project[]): string {
  return toCsv(
    ["project_key", "utility", "owner_code", "native_id", "name", "in_service_raw", "in_service_date", "in_service_precision",
      "center_lat", "center_lon", "center_basis", "location_confidence", "source_id", "source_page", "active"],
    rows.map((p) => [
      p.project_key, p.utility, p.owner_code ?? "not published", p.native_id, p.name, p.in_service.raw, p.in_service.date,
      p.in_service.precision, p.center?.lat, p.center?.lon, p.center?.basis ?? "no center",
      p.location_confidence ?? "needs review", p.source.source_id, p.source.page, p.active,
    ]),
  );
}

/** Rows from the same active dataset the API reads (fixture files in DATA_MODE=fixture). */
async function load(type: "matches" | "projects", view?: z.infer<typeof Query>["view"]) {
  if (isFixtureMode()) {
    const r = type === "matches" ? await getMatches({ view, limit: MAX_ROWS }) : await getProjects();
    if (isUnavailable(r)) throw new Error(r.reason);
    return r;
  }
  const db = await getDb();
  const dataset = await activeDataset(db);
  return type === "matches" ? q.matches(db, dataset, { view, limit: MAX_ROWS }) : q.projects(db, dataset, {});
}

export async function GET(req: Request) {
  const parsed = Query.safeParse(Object.fromEntries(new URL(req.url).searchParams));
  if (!parsed.success) return Response.json({ error: "invalid query", issues: parsed.error.issues.map((i) => i.message) }, { status: 400 });
  const { type, view } = parsed.data;
  try {
    const rows = (await load(type, view)).slice(0, MAX_ROWS);
    const body = type === "matches" ? matchesCsv(rows as MatchRow[]) : projectsCsv(rows as Project[]);
    return new Response(body, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="gridbridge-${type}${view ? `-${view}` : ""}.csv"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    console.error(`api /api/export: unavailable (${(err as Error)?.name})`);
    return Response.json({ unavailable: true, reason: "database error" }, { status: 503 });
  }
}
