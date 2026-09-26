export type VerifiedValidationStatus = "accepted" | "needs_review" | "rejected";

export type VerifiedUtilityRecord = {
  id: string;
  eia_utility_id: string;
  data_year: number;
  name: string;
  state_fips: string[];
  county_geoids: string[];
  source_ids: string[];
  validation_status: VerifiedValidationStatus;
  limitations: string[];
};

export type VerifiedFilters = {
  state?: string;
  county?: string;
  q?: string;
  page: number;
  limit: number;
};

export type VerifiedListResponse = {
  available: boolean;
  reason: string | null;
  dataset: string | null;
  generated_at: string | null;
  filters: VerifiedFilters;
  total: number;
  page: number;
  limit: number;
  records: VerifiedUtilityRecord[];
};

export type VerifiedCoverage = {
  schema_version: "verified-directory-v1";
  dataset: string;
  generated_at: string;
  data_year: 2024;
  source_vintages: Record<string, string | null>;
  counts: {
    sources: number;
    utilities: number;
    utility_activities: number;
    service_territory_rows: number;
    assertions: number;
    quarantine: number;
    utilities_by_validation_status: Record<string, number>;
    service_territory_by_validation_status: Record<string, number>;
    resolved_county_rows: number;
    unresolved_county_rows: number;
    conflicting_county_rows: number;
    rejected_county_rows: number;
    independently_corroborated_service_claims: 0;
    comparable_field_conflicts: number;
    unknown_utility_rows: number;
    county_identity_quarantine_rows: number;
  };
  limitations: string[];
};

export type VerifiedCoverageResponse = {
  available: boolean;
  reason: string | null;
  dataset: string | null;
  generated_at: string | null;
  coverage: VerifiedCoverage | null;
};
