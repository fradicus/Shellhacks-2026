import { cleanQuery, geocode } from "@/lib/geocode";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const query = cleanQuery(new URL(request.url).searchParams.get("q"));
  if (!query) return Response.json({ error: "Enter 3 to 200 characters." }, { status: 400 });
  try { return Response.json({ query, result: await geocode(query) }, { headers: { "Cache-Control": "no-store" } }); }
  catch { return Response.json({ query, result: null, error: "Location search is unavailable. Enter latitude and longitude instead." }, { status: 503 }); }
}
