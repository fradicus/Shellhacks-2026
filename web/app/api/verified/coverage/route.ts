import { rejectVerifiedCoverageParams } from "@/lib/verified/filters";
import { loadVerifiedCoverage } from "@/lib/verified/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    rejectVerifiedCoverageParams(new URL(request.url).searchParams);
    const payload = await loadVerifiedCoverage();
    return Response.json(payload, { status: payload.available ? 200 : 503, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json(
      { error: "invalid query", issues: [error instanceof Error ? error.message : "invalid query"] },
      { status: 400, headers: { "Cache-Control": "no-store" } },
    );
  }
}
