import "server-only";

import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { filterVerifiedUtilities, InvalidVerifiedQuery, validateVerifiedGeography } from "./filters";
import type {
  VerifiedCoverage, VerifiedCoverageResponse, VerifiedFilters, VerifiedListResponse, VerifiedUtilityRecord,
} from "./types";

const DATA_DIR = resolve(process.cwd(), "..", "data", "verified");
const GEOGRAPHY_PATH = resolve(process.cwd(), "..", "data", "national", "geography.json");
const MAX_RECORDS = 10_000;

type Envelope = {
  schema_version: string;
  dataset: string;
  generated_at: string;
  records: unknown[];
};

type Manifest = {
  schema_version: string;
  dataset: string;
  generated_at: string;
  files: Record<string, { sha256: string; records: number | null }>;
};

const hash = (value: Buffer) => createHash("sha256").update(value).digest("hex");

async function checkedJson<T>(name: string, manifest: Manifest): Promise<T> {
  const bytes = await readFile(resolve(DATA_DIR, name));
  if (!manifest.files[name] || hash(bytes) !== manifest.files[name].sha256) throw new Error(`${name} failed its manifest hash check`);
  return JSON.parse(bytes.toString("utf8")) as T;
}

function validUtilities(value: Envelope, manifest: Manifest): value is Envelope & { records: VerifiedUtilityRecord[] } {
  const statuses = new Set(["accepted", "needs_review", "rejected"]);
  return value.schema_version === "verified-directory-v1" && value.dataset === manifest.dataset
    && value.generated_at === manifest.generated_at && value.records.length <= MAX_RECORDS
    && value.records.every((raw) => {
      const item = raw as Partial<VerifiedUtilityRecord> | null;
      return !!item && typeof item.id === "string" && typeof item.eia_utility_id === "string"
        && typeof item.name === "string" && item.data_year === 2024
        && Array.isArray(item.state_fips) && item.state_fips.every((code) => /^\d{2}$/.test(code))
        && Array.isArray(item.county_geoids) && item.county_geoids.every((code) => /^\d{5}$/.test(code))
        && Array.isArray(item.source_ids) && item.source_ids.every((id) => typeof id === "string")
        && typeof item.validation_status === "string" && statuses.has(item.validation_status)
        && Array.isArray(item.limitations) && item.limitations.every((text) => typeof text === "string");
    });
}

async function loadDirectory() {
  const manifestBytes = await readFile(resolve(DATA_DIR, "manifest.json"));
  const manifest = JSON.parse(manifestBytes.toString("utf8")) as Manifest;
  if (manifest.schema_version !== "verified-directory-v1" || !/^[a-f0-9]{64}$/.test(manifest.dataset)) {
    throw new Error("verified manifest failed its public shape check");
  }
  const [utilities, coverage, geography] = await Promise.all([
    checkedJson<Envelope>("utilities.json", manifest),
    checkedJson<VerifiedCoverage>("coverage.json", manifest),
    readFile(GEOGRAPHY_PATH, "utf8").then((value) => JSON.parse(value) as {
      states: { state_fips: string }[]; counties: { county_geoid: string; state_fips: string }[];
    }),
  ]);
  if (!validUtilities(utilities, manifest) || coverage.dataset !== manifest.dataset
    || coverage.generated_at !== manifest.generated_at || coverage.schema_version !== "verified-directory-v1") {
    throw new Error("verified artifacts failed their public shape check");
  }
  return { manifest, utilities: utilities.records, coverage, geography };
}

export async function loadVerifiedDirectory(filters: VerifiedFilters): Promise<VerifiedListResponse> {
  try {
    const source = await loadDirectory();
    const geographyIssue = validateVerifiedGeography(filters, source.geography);
    if (geographyIssue) throw new InvalidVerifiedQuery(geographyIssue);
    const filtered = filterVerifiedUtilities(source.utilities, filters);
    const offset = (filters.page - 1) * filters.limit;
    const records = filtered.slice(offset, offset + filters.limit).map((record) => ({
      id: record.id,
      eia_utility_id: record.eia_utility_id,
      data_year: record.data_year,
      name: record.name,
      state_fips: record.state_fips,
      county_geoids: record.county_geoids,
      source_ids: record.source_ids,
      validation_status: record.validation_status,
      limitations: record.limitations,
    }));
    return {
      available: true, reason: null, dataset: source.manifest.dataset, generated_at: source.manifest.generated_at,
      filters, total: filtered.length, page: filters.page, limit: filters.limit, records,
    };
  } catch (error) {
    if (error instanceof InvalidVerifiedQuery) throw error;
    return {
      available: false, reason: "Verified public directory is unavailable.", dataset: null, generated_at: null,
      filters, total: 0, page: filters.page, limit: filters.limit, records: [],
    };
  }
}

export async function loadVerifiedCoverage(): Promise<VerifiedCoverageResponse> {
  try {
    const source = await loadDirectory();
    return {
      available: true, reason: null, dataset: source.manifest.dataset, generated_at: source.manifest.generated_at,
      coverage: source.coverage,
    };
  } catch {
    return { available: false, reason: "Verified coverage is unavailable.", dataset: null, generated_at: null, coverage: null };
  }
}
