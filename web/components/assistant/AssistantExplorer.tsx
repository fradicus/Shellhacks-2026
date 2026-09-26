"use client";

import { NationalExplorer } from "@/components/national/NationalExplorer";
import type { NationalAssistantRenderer, NationalExplorerPayload } from "@/lib/national/types";
import { AssistantPanel } from "./AssistantPanel";

export function AssistantExplorer({ initial }: { initial: NationalExplorerPayload }) {
  const renderAssistant: NationalAssistantRenderer = (controller) => (
    <AssistantPanel controller={controller} planningRegions={initial.facets.planningRegions} />
  );
  return <NationalExplorer initial={initial} basePath="/assistant" renderAssistant={renderAssistant} />;
}
