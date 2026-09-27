import { parseWaterQuery } from "../../../../lib/operations/contracts";
import { failureResponse, serviceFailure } from "../../../../lib/operations/errors";
import { water } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  let query: ReturnType<typeof parseWaterQuery>;
  try {
    query = parseWaterQuery(new URL(request.url).searchParams);
  } catch {
    return failureResponse("invalid_input", "Invalid water request");
  }
  try {
    return Response.json(await water(query), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = serviceFailure(error);
    console.error(`api /api/operations/water: ${code} (${(error as Error)?.name})`);
    return failureResponse(code);
  }
}
