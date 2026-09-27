import type { Metadata } from "next";
import { OperationsDesk } from "@/components/operations/OperationsDesk";

export const metadata: Metadata = {
  title: "Field operations | Common Ground",
  description: "Evidence-bound worksite, conditions, truck-route, and actual-outcome planning for one estimator.",
};

export default function OperationsPage() {
  return <OperationsDesk />;
}
