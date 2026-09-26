import { z } from "zod";
import { handle } from "@/lib/server/http";
import { sources } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  return handle(req, z.strictObject({}), (_q, db, dataset) => sources(db, dataset));
}
