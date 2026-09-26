import { z } from "zod";
import { handle } from "@/lib/server/http";
import { pair } from "@/lib/server/queries";

export const dynamic = "force-dynamic";

const Id = z.string().min(3).max(300);

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  // Next has already decoded the segment; decoding again would turn a literal "%25" into "%" (or throw on "%zz").
  const id = Id.safeParse((await params).id);
  if (!id.success) return Response.json({ error: "invalid pair id" }, { status: 400 });
  return handle(req, z.strictObject({}), (_q, db, dataset) => pair(db, dataset, id.data));
}
