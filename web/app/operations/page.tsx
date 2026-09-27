import type { Metadata } from "next";
import { OperationsDesk } from "@/components/operations/OperationsDesk";

export const metadata: Metadata = {
  title: "Field operations | GridBridge",
  description: "Evidence-bound worksite, conditions, truck-route, and actual-outcome planning for one estimator.",
};

export default async function OperationsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const viewParam = raw.view;
  const view = (Array.isArray(viewParam) ? viewParam[0] : viewParam) === "factors" ? "factors" : "planning";
  return <OperationsDesk initialView={view} />;
}
