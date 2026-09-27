import { z } from "zod";
import { NationalQuery } from "../national/filters";
import { AssistantActionSchema } from "./commands";

export const AssistantFiltersSchema = NationalQuery.omit({ planningregion: true }).extend({
  planningRegion: z.string().trim().min(1).max(80).optional(),
  page: z.number().int().min(1).max(10000), limit: z.number().int().min(1).max(100),
}).strict().refine((v) => !v.from || !v.to || v.from <= v.to, "Reversed date interval");
export const AssistantRequestSchema = z.strictObject({
  message: z.string().trim().min(1).max(1000), filters: AssistantFiltersSchema,
  dataset: z.string().min(1).max(200).nullable(),
  visibleProjectIds: z.array(z.string().min(1).max(240)).max(100).refine((v) => new Set(v).size === v.length, "Duplicate project IDs"),
  requestId: z.string().min(1).max(80).regex(/^[A-Za-z0-9_.:-]+$/),
}).refine((v) => v.dataset !== null || v.visibleProjectIds.length === 0, "Visible projects require their dataset");
export type AssistantRequest = z.infer<typeof AssistantRequestSchema>;
export const HelpTopicSchema = z.enum(["capabilities", "data_coverage", "overlap_rules", "source_quality", "construction_dates", "weather_routes"]);
export const ModelDecisionSchema = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("action"), action: AssistantActionSchema }),
  z.strictObject({ kind: z.literal("help"), topic: HelpTopicSchema }),
  z.strictObject({ kind: z.literal("clarification"), message: z.string().trim().min(1).max(300) }),
  z.strictObject({ kind: z.literal("unsupported") }),
]);
export type ModelDecision = z.infer<typeof ModelDecisionSchema>;
export type AssistantStatus = { ready: boolean; mode: "gemini" | "unavailable"; reason: string | null; model: string | null };
export type AssistantResponse = {
  status: "action" | "clarification" | "answer" | "unsupported" | "unavailable";
  message: string; action: z.infer<typeof AssistantActionSchema> | null; requestId: string;
  model: string | null; provider: "gemini" | null;
  dataset: string | null;
};
