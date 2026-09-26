import { z } from "zod";
import { BBOX, VIEW, handle } from "@/lib/server/http";
import { projects } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

// `view` is accepted for symmetry with /api/matches; projects themselves aren't view-scoped.
const Query = z.strictObject({ bbox: BBOX.optional(), view: VIEW.optional() });

export function GET(req: Request) {
  return handle(req, Query, (q, db, dataset) => projects(db, dataset, q));
}
