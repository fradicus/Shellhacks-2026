import { parseSiteQuery } from "../../../../lib/operations/contracts";
import { failureResponse, serviceFailure } from "../../../../lib/operations/errors";
import { site } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  let query: ReturnType<typeof parseSiteQuery>;
  try {
    query = parseSiteQuery(new URL(request.url).searchParams);
  } catch {
    return failureResponse("invalid_input", "Invalid site request");
  }
  try {
    return Response.json(await site(query), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = serviceFailure(error);
    console.error(`api /api/operations/site: ${code} (${(error as Error)?.name})`);
    return failureResponse(code);
  }
}
