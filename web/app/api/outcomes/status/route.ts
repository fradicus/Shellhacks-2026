import { modelStatus } from "@/lib/outcomes/model";
import { loadOutcomeModel } from "@/lib/outcomes/server";

export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const headers = { "Cache-Control": "no-store" };
  if (new URL(request.url).search) return Response.json({ error: "Query parameters are not supported." }, { status: 400, headers });
  return Response.json(modelStatus(await loadOutcomeModel()), { headers });
}
