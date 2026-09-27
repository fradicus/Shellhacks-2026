import { loadNationalProject } from "@/lib/national/server";

export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "no-store" };

export async function GET(req: Request) {
  const params = new URL(req.url).searchParams;
  const id = params.get("id");
  const dataset = params.get("dataset");
  if ([...params.keys()].some((key) => !["id", "dataset"].includes(key) || params.getAll(key).length !== 1)
    || !id || id.length > 512 || /[\u0000-\u001f\u007f]/.test(id)
    || !dataset || !/^[a-zA-Z0-9._:-]{1,128}$/.test(dataset)) {
    return Response.json({ available: false, reason: "A valid project ID and dataset are required." }, { status: 400, headers });
  }
  const detail = await loadNationalProject(id, dataset);
  return Response.json(detail, { status: detail.available ? 200 : detail.status, headers });
}
