import { parseQuery } from "@/lib/national-pairs/query";
import { loadCandidatePairs, PairReadError } from "@/lib/national-pairs/server";

export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "no-store" };
export async function GET(request: Request) {
  let query;
  try { query = parseQuery(new URL(request.url).searchParams); }
  catch { return Response.json({ available: false, reason: "Invalid candidate query." }, { status: 400, headers }); }
  try { return Response.json(await loadCandidatePairs(query), { headers }); }
  catch (error) {
    return Response.json({ available: false, reason: error instanceof PairReadError ? error.message : "Nearby candidates are unavailable. Please retry." },
      { status: error instanceof PairReadError ? error.status : 503, headers });
  }
}
