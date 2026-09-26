import { reference } from "@/lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (new URL(request.url).search) return Response.json({ error: "Reference does not accept query parameters" }, { status: 400, headers: { "Cache-Control": "no-store" } });
  return Response.json(await reference(), { headers: { "Cache-Control": "no-store" } });
}
