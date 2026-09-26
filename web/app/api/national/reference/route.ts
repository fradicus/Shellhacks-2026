import { loadNationalReference } from "@/lib/national/server";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (new URL(req.url).searchParams.size) {
    return Response.json({ error: "invalid query", issues: ["reference endpoint accepts no query parameters"] }, { status: 400 });
  }
  const reference = await loadNationalReference();
  return Response.json(reference, {
    status: reference.referenceAvailable ? 200 : 503,
    headers: { "Cache-Control": "no-store" },
  });
}
