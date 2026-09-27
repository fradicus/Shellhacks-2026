import { failureResponse, serviceFailure } from "../../../../lib/operations/errors";
import { reference } from "../../../../lib/operations/service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  if (new URL(request.url).search) return failureResponse("invalid_input", "Reference does not accept query parameters");
  try {
    return Response.json(await reference(), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const code = serviceFailure(error);
    console.error(`api /api/operations/reference: ${code} (${(error as Error)?.name})`);
    return failureResponse(code);
  }
}
