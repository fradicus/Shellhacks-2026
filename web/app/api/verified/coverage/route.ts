import { loadVerifiedCoverage } from "@/lib/verified/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload = await loadVerifiedCoverage();
  return Response.json(payload, { status: payload.available ? 200 : 503, headers: { "Cache-Control": "no-store" } });
}
