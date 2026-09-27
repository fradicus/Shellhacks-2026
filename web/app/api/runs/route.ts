import { z } from "zod";
import { handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

// No active dataset needed: a failed first load must still be reported. 404 when no run is stored.
export function GET(req: Request) {
  return handleRead(req, z.strictObject({}), (_q, signal) => repository.latestRun(signal));
}
