"use client";

import { NationalExplorer } from "@/components/national/NationalExplorer";
import type { NationalAssistantRenderer, NationalExplorerPayload } from "@/lib/national/types";
import { AssistantPanel } from "./AssistantPanel";

const renderAssistant: NationalAssistantRenderer = (controller) => <AssistantPanel controller={controller} />;

export function AssistantExplorer({ initial }: { initial: NationalExplorerPayload }) {
  return <NationalExplorer initial={initial} basePath="/assistant" renderAssistant={renderAssistant} />;
}
