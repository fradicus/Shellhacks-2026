import "server-only";
import type { LoadedModel } from "./model";
import { createModelLoader } from "./model";

const loadCached = createModelLoader();
export async function loadOutcomeModel(): Promise<LoadedModel> {
  const env = { OUTCOMES_MODEL_PATH: process.env.OUTCOMES_MODEL_PATH,
    OUTCOMES_APPROVED_SHA256: process.env.OUTCOMES_APPROVED_SHA256, OUTCOMES_APPROVED_AT: process.env.OUTCOMES_APPROVED_AT };
  return loadCached(env);
}
