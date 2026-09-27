import { z } from "zod";
import { LIMIT, MAX_DISTANCE, VIEW, handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

const Query = z.strictObject({ view: VIEW.optional(), maxDistance: MAX_DISTANCE.optional(), limit: LIMIT.optional() });

export function GET(req: Request) {
  return handleRead(req, Query, (q, signal) => repository.matches(q, signal));
}
