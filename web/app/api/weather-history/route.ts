import { parseConditionsQuery } from "@/lib/operations/contracts";
import { historyAt } from "@/lib/weather-history";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Committed NOAA station history only; this route makes no upstream calls.
export async function GET(request: Request) {
  let point;
  try { point = parseConditionsQuery(new URL(request.url).searchParams); }
  catch { return Response.json({ error: "Invalid weather history request" }, { status: 400 }); }
  try {
    const history = await historyAt(point);
    return Response.json({ request: point, history }, { headers: { "Cache-Control": "public, max-age=3600" } });
  } catch {
    return Response.json({ request: point, history: null, error: "Weather history is unavailable." }, { status: 503 });
  }
}
