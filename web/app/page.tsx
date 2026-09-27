import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";
import { isFixtureMode } from "@/lib/data";

export const metadata: Metadata = {
  title: "Common Ground — Every mile. Connected.",
  description: "Discover nearby transmission projects, compare public utility filings, and find the evidence for your next coordination conversation.",
};

export default function Home() {
  return <LandingPage fixtureMode={isFixtureMode()} />;
}
