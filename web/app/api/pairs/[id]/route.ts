import { z } from "zod";
import { handle } from "@/lib/server/http";
import { pair } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

const Id = z.string().min(3).max(300);

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const id = Id.safeParse(decodeURIComponent((await params).id));
  if (!id.success) return Response.json({ error: "invalid pair id" }, { status: 400 });
  return handle(req, z.strictObject({}), (_q, db, dataset) => pair(db, dataset, id.data));
}
