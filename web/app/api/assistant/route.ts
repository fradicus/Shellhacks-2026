import { createAssistantHandlers } from "../../../lib/assistant/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const handlers = createAssistantHandlers();
export const GET = handlers.GET;
export const POST = handlers.POST;
