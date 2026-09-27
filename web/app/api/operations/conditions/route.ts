import { parseConditionsQuery } from "../../../../lib/operations/contracts";
import { failureResponse, serviceFailure } from "../../../../lib/operations/errors";
import { conditions } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  let point: ReturnType<typeof parseConditionsQuery>;
  try {
    point = parseConditionsQuery(new URL(request.url).searchParams);
  } catch {
    return failureResponse("invalid_input", "Invalid conditions request");
  }
  try {
    return Response.json(await conditions(point), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = serviceFailure(error);
    console.error(`api /api/operations/conditions: ${code} (${(error as Error)?.name})`);
    return failureResponse(code);
  }
}
