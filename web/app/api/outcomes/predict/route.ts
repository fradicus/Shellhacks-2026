import { predict } from "@/lib/outcomes/model";
import { loadOutcomeModel } from "@/lib/outcomes/server";

export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  const headers = { "Cache-Control": "no-store" };
  try {
    if (new URL(request.url).search || request.headers.get("content-type")?.split(";")[0] !== "application/json") {
      return Response.json({ error: "A JSON body without query parameters is required." }, { status: 400, headers });
    }
    const reader = request.body?.getReader();
    if (!reader) throw new Error("missing body");
    const chunks: Uint8Array[] = [];
    let length = 0;
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > 4096) { await reader.cancel(); return Response.json({ error: "Request body exceeds limit." }, { status: 413, headers }); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const input: unknown = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    const response = predict(await loadOutcomeModel(), input);
    return Response.json(response, { status: response.status === "invalid" ? 400 : 200, headers });
  } catch {
    return Response.json({ ...predict(null, null), reason: "Malformed or unavailable request." }, { status: 400, headers });
  }
}
