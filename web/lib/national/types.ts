import type { ReactNode } from "react";

export type NationalStatus =
  | "planned"
  | "under_construction"
  | "proposed"
  | "in_service"
  | "cancelled"
  | "unknown";

export interface NationalSource {
  _id: string;
  title: string;
  publisher: string;
  authority: "federal_government" | "state_government" | "regional_planning_organization" | "utility" | "sponsor_supplied";
  role: "project_plan" | "utility_directory" | "service_territory_reference" | "geography_reference" | "planning_directory" | "existing_infrastructure_reference";
  landing_url: string | null;
  local_reference?: string | null;
  access_policy?: "public_document" | "metadata_only" | "catalog_only";
  download_url: string | null;
  publication_date: string | null;
  vintage: string | null;
  retrieved_at: string | null;
  sha256: string | null;
  public_status: "verified_public" | "public_with_banner" | "sponsor_supplied" | "catalog_only";
  import_status: "imported" | "reference_only" | "catalogued" | "unavailable";
  planning_region: string | null;
  states: string[];
  notes: string[];
}

export interface NationalProject {
  _id: string;
  source_id: string;
  native_id: string;
  name: string;
  description?: string | null;
  owner: string | null;
  other_owners: string[];
  planning_region: string | null;
  states: string[];
  counties: string[];
  geography_basis: string | null;
  status: string | null;
  status_group: NationalStatus;
  in_service: { raw: string | null; value: string | null; precision: "day" | "month" | "year" | "unknown" };
  center: { lat: number; lon: number; basis: "one" | "two" | "source_point"; evidence: string } | null;
  location_review: "confirmed" | "needs_review" | "rejected" | "unreviewed" | "unlocated";
  evidence: { page: number | null; sheet: string | null; row: number | null; raw: Record<string, unknown> };
}

export interface GeoBounds {
  west: number;
  south: number;
  east: number;
  north: number;
  crosses_antimeridian: boolean;
  fit_west: number;
  fit_east_unwrapped: number;
}

export interface NationalState {
  state_fips: string;
  usps: string;
  name: string;
  scope: "state" | "district" | "territory";
  selectable_primary: boolean;
  census_region_code: string | null;
  census_division_code: string | null;
  bounds: GeoBounds | null;
}

export interface NationalCounty {
  county_geoid: string;
  state_fips: string;
  county_fips: string;
  name: string;
  full_name: string;
  state_usps: string;
  state_name: string;
  scope: "state" | "district" | "territory";
  selectable_primary: boolean;
  bounds: GeoBounds | null;
}

export interface NationalGeography {
  schema_version: "national-geography-v1";
  authority: "U.S. Census Bureau";
  provenance: { sources: unknown; notes: string[] };
  counts: Record<string, unknown>;
  states: NationalState[];
  counties: NationalCounty[];
  regions: { region_code: string; name: string; bounds: GeoBounds | null }[];
  divisions: { division_code: string; name: string; bounds: GeoBounds | null }[];
}

export interface NationalCoverage {
  schema_version: "national-coverage-v1";
  projects_total: number;
  located_count: number;
  sources: {
    source_id: string;
    project_count: number;
    located_count: number;
    active_status_count: number;
    unknown_state_count: number;
    unknown_county_count: number;
    status_counts: Record<string, number>;
  }[];
  failures: { source_id: string; message: string }[];
  notes: string[];
}

export interface NationalFilters {
  region?: string;
  state?: string;
  county?: string;
  planningRegion?: string;
  owner?: string;
  status?: NationalStatus;
  from?: string;
  to?: string;
  text?: string;
  page: number;
  limit: number;
}

export type NationalFilterKey = Exclude<keyof NationalFilters, "page" | "limit">;

export type NationalFilterAction =
  | { type: "filters.patch"; filters: Partial<Omit<NationalFilters, "page" | "limit">> }
  | { type: "filters.clear"; keys: NationalFilterKey[] }
  | { type: "filters.reset" }
  | { type: "project.select"; projectId: string | null }
  | { type: "geography.focus"; kind: "region" | "state" | "county"; code: string };

export interface NationalActionResult {
  ok: boolean;
  reason?: string;
}

export interface NationalExplorerController {
  filters: Readonly<NationalFilters>;
  results: Readonly<{ ids: string[]; total: number; located: number; unlocated: number }>;
  availability: Readonly<{ loading: boolean; available: boolean; mode: NationalExplorerPayload["mode"] }>;
  reference: Readonly<{
    regions: NationalGeography["regions"];
    states: NationalState[];
    counties: NationalCounty[];
    sources: NationalSource[];
  }>;
  selectedProjectId: string | null;
  applyAction(action: NationalFilterAction): NationalActionResult;
  reset(): void;
  undo(): NationalActionResult;
}

export type NationalAssistantRenderer = (controller: NationalExplorerController) => ReactNode;

export interface NationalReference {
  geography: NationalGeography | null;
  sources: NationalSource[];
  coverage: NationalCoverage | null;
  referenceAvailable: boolean;
  reason?: string;
}

export interface NationalExplorerPayload extends NationalReference {
  available: boolean;
  mode: "atlas" | "snapshot" | "unavailable";
  dataset: string | null;
  reason?: string;
  invalidQuery?: boolean;
  filters: NationalFilters;
  projects: NationalProject[];
  mapProjects: NationalProject[];
  total: number;
  locatedTotal: number;
  unlocatedTotal: number;
  page: number;
  limit: number;
  mapTruncated: boolean;
  facets: {
    planningRegions: string[];
    owners: string[];
    statuses: NationalStatus[];
  };
}
