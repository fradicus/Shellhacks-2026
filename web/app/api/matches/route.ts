import { z } from "zod";
import { LIMIT, MAX_DISTANCE, VIEW, handle } from "@/lib/server/http";
import { matches } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

const Query = z.strictObject({ view: VIEW.optional(), maxDistance: MAX_DISTANCE.optional(), limit: LIMIT.optional() });

export function GET(req: Request) {
  return handle(req, Query, (q, db, dataset) => matches(db, dataset, q));
}
