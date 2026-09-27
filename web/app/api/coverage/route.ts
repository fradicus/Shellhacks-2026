import { z } from "zod";
import { handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

export function GET(req: Request) {
  return handleRead(req, z.strictObject({}), (_q, signal) => repository.coverage(signal));
}
