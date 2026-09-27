"use client";

import { useEffect, useMemo } from "react";
import { NationalExplorer } from "@/components/national/NationalExplorer";
import type { NationalAssistantRenderer, NationalExplorerController, NationalSummaryPayload } from "@/lib/national/types";
import { AssistantHost, useAssistantHost, type AssistantRegistration } from "./AssistantHost";

function RegistrationBridge({ value }: { value: AssistantRegistration }) {
  const host = useAssistantHost();
  useEffect(() => host?.register(value), [host, value]);
  return null;
}

function ConnectedExplorer({ initial }: { initial: NationalSummaryPayload }) {
  const renderAssistant = useMemo<NationalAssistantRenderer>(() => function AssistantRegistrationRenderer(controller: NationalExplorerController) {
    return <RegistrationBridge value={{ controller, planningRegions: initial.facets.planningRegions, owners: initial.facets.owners, dataset: initial.dataset }} />;
  }, [initial.dataset, initial.facets.owners, initial.facets.planningRegions]);
  return <NationalExplorer initial={initial} basePath="/assistant" renderAssistant={renderAssistant} />;
}

export function AssistantExplorer({ initial }: { initial: NationalSummaryPayload }) {
  const host = useAssistantHost();
  return host ? <ConnectedExplorer initial={initial} /> : <AssistantHost><ConnectedExplorer initial={initial} /></AssistantHost>;
}
