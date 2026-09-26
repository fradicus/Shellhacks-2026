import { reference } from "@/lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET() { return Response.json(await reference(), { headers: { "Cache-Control": "no-store" } }); }
