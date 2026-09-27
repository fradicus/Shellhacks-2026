import type { Match, Project } from "@/lib/types";

export function filedOwnerLabel(project: Project | null): string | null {
  return project?.utility === "GPC" && project.owner_code
    ? `Filed owner code ${project.owner_code} · Georgia filing` : null;
}

export function pairDescription(state: Match["review_state"]): string {
  return state === "confirmed"
    ? "A reviewed coordination lead worth a planner's conversation, not a compliance finding or a savings estimate."
    : state === "rejected"
      ? "A rejected pair retained for audit. It is not a validated coordination opportunity."
      : "A candidate pair that still needs evidence review before it can be treated as a coordination opportunity.";
}
