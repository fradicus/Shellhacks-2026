import { z } from "zod";
import { BBOX, VIEW, handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

// `view` is accepted for symmetry with /api/matches; projects themselves aren't view-scoped.
const Query = z.strictObject({ bbox: BBOX.optional(), view: VIEW.optional() });

export function GET(req: Request) {
  return handleRead(req, Query, ({ bbox }, signal) => repository.projects({ bbox }, signal));
}
