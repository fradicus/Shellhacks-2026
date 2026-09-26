import { z } from "zod";
import { handle } from "@/lib/server/http";
import { extractions } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

const Query = z.strictObject({ source: z.string().regex(/^[A-Za-z0-9._-]{1,100}$/).optional() });

export function GET(req: Request) {
  return handle(req, Query, (q, db, dataset) => extractions(db, dataset, q));
}
