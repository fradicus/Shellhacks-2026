import { RouteRequestSchema, type RouteRequest } from "../../../../lib/operations/contracts";
import { failureResponse, inputFailure, OperationsError, serviceFailure } from "../../../../lib/operations/errors";
import { route } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_BODY = 4096;
const BODY_DEADLINE_MS = 2000;

async function readBody(request: Request): Promise<RouteRequest> {
  if (!request.headers.get("content-type")?.includes("application/json") || !request.body) throw new OperationsError("invalid_input");
  if (Number(request.headers.get("content-length")) > MAX_BODY) throw new OperationsError("body_too_large");
  const reader = request.body.getReader();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const read = async () => {
      let size = 0;
      const chunks: Uint8Array[] = [];
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        size += part.value.length;
        if (size > MAX_BODY) throw new OperationsError("body_too_large");
        chunks.push(part.value);
      }
      return JSON.parse(Buffer.concat(chunks).toString("utf8"));
    };
    const value = await Promise.race([read(), new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new OperationsError("timeout", "Request body deadline exceeded")), BODY_DEADLINE_MS);
    })]);
    return RouteRequestSchema.parse(value);
  } finally {
    clearTimeout(timer);
    void reader.cancel().catch(() => {});
  }
}

export async function POST(request: Request) {
  let input: RouteRequest;
  try {
    input = await readBody(request);
  } catch (error) {
    const code = inputFailure(error);
    return failureResponse(code, code === "invalid_input" ? "Invalid route request" : undefined);
  }
  try {
    return Response.json(await route(input), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = serviceFailure(error);
    if (code !== "departure_window") console.error(`api /api/operations/route: ${code} (${(error as Error)?.name})`);
    return failureResponse(code);
  }
}
