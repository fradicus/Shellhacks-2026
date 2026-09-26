import { z } from "zod";
import { handleDb } from "@/lib/server/http";
import { latestRun } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

// No active dataset needed: a failed first load must still be reported. 404 when no run is stored.
export function GET(req: Request) {
  return handleDb(req, z.strictObject({}), (_q, db) => latestRun(db));
}
