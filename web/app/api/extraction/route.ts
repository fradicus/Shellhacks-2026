import { z } from "zod";
import { handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

const Query = z.strictObject({ source: z.string().regex(/^[A-Za-z0-9._-]{1,100}$/).optional() });

export function GET(req: Request) {
  return handleRead(req, Query, (q, signal) => repository.extractions(q, signal));
}
