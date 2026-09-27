import { z } from "zod";
import { handleRead } from "@/lib/server/http";
import { repository } from "@/lib/server/repository";

export const dynamic = "force-dynamic";

const Id = z.string().min(3).max(300);

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  // Next has already decoded the segment; decoding again would turn a literal "%25" into "%" (or throw on "%zz").
  const id = Id.safeParse((await params).id);
  if (!id.success) return Response.json({ error: "invalid pair id" }, { status: 400 });
  return handleRead(req, z.strictObject({}), (_q, signal) => repository.pair(id.data, signal));
}
