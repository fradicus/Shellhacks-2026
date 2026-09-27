import { committedStations } from "@/lib/weather-history";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Coverage layer: committed NOAA stations only (no upstream calls). Points elsewhere still get a live lookup.
export async function GET() {
  try { return Response.json(await committedStations(), { headers: { "Cache-Control": "public, max-age=3600" } }); }
  catch { return Response.json({ error: "Station list unavailable." }, { status: 503 }); }
}
