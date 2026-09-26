import "server-only";
import { loadApprovedModel } from "./model";

export const loadOutcomeModel = () => loadApprovedModel({
  OUTCOMES_MODEL_PATH: process.env.OUTCOMES_MODEL_PATH,
  OUTCOMES_APPROVED_SHA256: process.env.OUTCOMES_APPROVED_SHA256,
});
