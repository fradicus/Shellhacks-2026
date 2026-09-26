import { RouteRequestSchema } from "@/lib/operations/contracts";
import { route } from "@/lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    if (!request.headers.get("content-type")?.includes("application/json") || Number(request.headers.get("content-length")) > 4096 || !request.body) throw new Error("Invalid body");
    reader = request.body.getReader(); let size = 0; const chunks: Uint8Array[] = [];
    const read = async () => { while (true) { const part = await reader!.read(); if (part.done) break; size += part.value.length; if (size > 4096) throw new Error("Body too large"); chunks.push(part.value); } return JSON.parse(Buffer.concat(chunks).toString("utf8")); };
    const value = await Promise.race([read(), new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error("Body deadline")), 2000); })]);
    clearTimeout(timer);
    return Response.json(await route(RouteRequestSchema.parse(value)), { headers: { "Cache-Control": "no-store" } });
  } catch { return Response.json({ error: "Invalid route request or departure outside seven-day window" }, { status: 400, headers: { "Cache-Control": "no-store" } }); }
  finally { clearTimeout(timer); void reader?.cancel().catch(() => {}); }
}
