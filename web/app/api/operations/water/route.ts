import { parseWaterQuery } from "../../../../lib/operations/contracts";
import { water } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  try { return Response.json(await water(parseWaterQuery(new URL(request.url).searchParams)), { headers: { "Cache-Control": "no-store" } }); }
  catch { return Response.json({ error: "Invalid water request" }, { status: 400, headers: { "Cache-Control": "no-store" } }); }
}
