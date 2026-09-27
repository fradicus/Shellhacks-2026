import type { NationalProjectSummary } from "../national/types";

export interface CandidatePair {
  id: string;
  a: string;
  b: string;
  distance_mi: number;
  drive_mi: number;
  route: {
    polyline: string;
    start: { lat: number; lon: number } | null;
    end: { lat: number; lon: number } | null;
    provider: string;
    data_source: string;
    computed_at: string;
  };
  time_gap_days: number | null;
  band: 0 | 1;
  rank: number;
  tier: "confirmed" | "official" | "tentative";
  rule_version: string;
  identity_version: string;
}
export interface CandidatePage {
  available: true;
  dataset: string;
  pairs: CandidatePair[];
  projects: NationalProjectSummary[];
  total: number;
  offset: number;
  nextOffset: number | null;
}
export interface CandidateError { available: false; reason: string }
