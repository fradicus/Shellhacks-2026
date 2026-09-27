import { recentAt, STATION_ID } from "@/lib/weather-history";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Latest ~13 months of NOAA daily observations for stations chosen by /api/weather-history. Station ids only; no free text.
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const rain = params.get("rain") ?? "", wind = params.get("wind");
  if (!STATION_ID.test(rain) || (wind !== null && wind !== "" && !STATION_ID.test(wind))) return Response.json({ error: "Invalid station id" }, { status: 400 });
  try { return Response.json({ recent: await recentAt(rain, wind || null) }, { headers: { "Cache-Control": "public, max-age=3600" } }); }
  catch { return Response.json({ recent: null, error: "Recent NOAA observations are unavailable right now." }, { status: 503 }); }
}
