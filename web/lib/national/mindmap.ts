import type {
  NationalGeography,
  NationalProject,
  NationalStatus,
} from "./types";

export const MIND_MAP_PROJECT_LIMIT = 2_000;
export const MIND_MAP_PLACE_PREVIEW = 12;

const STATUS_LABEL: Record<NationalStatus, string> = {
  planned: "Planned",
  under_construction: "Under construction",
  proposed: "Proposed",
  in_service: "In service",
  cancelled: "Cancelled",
  unknown: "Status unknown",
};

export type MindMapPlaceKind = "facility" | "county" | "unknown";

export interface MindMapProjectLeaf {
  id: string;
  nativeId: string;
  name: string;
  owner: string | null;
  status: NationalStatus;
  statusLabel: string;
  located: boolean;
  planningRegion: string | null;
}

export interface MindMapPlaceNode {
  id: string;
  label: string;
  kind: MindMapPlaceKind;
  projectCount: number;
  locatedCount: number;
  projects: MindMapProjectLeaf[];
}

export interface MindMapStateNode {
  code: string;
  name: string;
  projectCount: number;
  locatedCount: number;
  places: MindMapPlaceNode[];
}

export interface MindMapRegionNode {
  code: string;
  name: string;
  projectCount: number;
  locatedCount: number;
  states: MindMapStateNode[];
}

export interface MindMapChartSlice {
  key: string;
  label: string;
  count: number;
}

export interface MindMapTree {
  regions: MindMapRegionNode[];
  charts: {
    byRegion: MindMapChartSlice[];
    byStatus: MindMapChartSlice[];
    byOwner: MindMapChartSlice[];
  };
  meta: {
    total: number;
    included: number;
    truncated: boolean;
    limit: number;
    notes: string[];
  };
}

const UNKNOWN_REGION = { code: "unknown", name: "Unknown region" };
const UNKNOWN_STATE = { code: "unknown", name: "Unknown state" };

function placeFor(
  project: NationalProject,
  geography: NationalGeography | null,
): { id: string; label: string; kind: MindMapPlaceKind } {
  const facility = project.location_verification?.points.find((point) => point.facility_name)?.facility_name?.trim();
  if (facility) {
    return { id: `facility:${facility.toLocaleLowerCase("en-US")}`, label: facility, kind: "facility" };
  }
  const countyCode = project.counties[0];
  if (countyCode) {
    const county = geography?.counties.find((item) => item.county_geoid === countyCode);
    return {
      id: `county:${countyCode}`,
      label: county?.full_name ?? `County ${countyCode}`,
      kind: "county",
    };
  }
  return { id: "unknown", label: "Unknown place", kind: "unknown" };
}

function leaf(project: NationalProject): MindMapProjectLeaf {
  return {
    id: project._id,
    nativeId: project.native_id,
    name: project.name,
    owner: project.owner,
    status: project.status_group,
    statusLabel: STATUS_LABEL[project.status_group],
    located: project.center !== null,
    planningRegion: project.planning_region,
  };
}

function sortByCountThenName<T extends { projectCount?: number; count?: number; name?: string; label?: string }>(
  items: T[],
): T[] {
  return [...items].sort((a, b) => {
    const countA = a.projectCount ?? a.count ?? 0;
    const countB = b.projectCount ?? b.count ?? 0;
    if (countB !== countA) return countB - countA;
    const nameA = a.name ?? a.label ?? "";
    const nameB = b.name ?? b.label ?? "";
    return nameA.localeCompare(nameB);
  });
}

/** Build region → state → place → electrical project tree from imported records only. */
export function buildMindMapTree(
  projects: NationalProject[],
  geography: NationalGeography | null,
  options?: { limit?: number },
): MindMapTree {
  const limit = options?.limit ?? MIND_MAP_PROJECT_LIMIT;
  const truncated = projects.length > limit;
  const included = projects.slice(0, limit);

  const regionMeta = new Map<string, { name: string }>();
  regionMeta.set(UNKNOWN_REGION.code, { name: UNKNOWN_REGION.name });
  for (const region of geography?.regions ?? []) {
    regionMeta.set(region.region_code, { name: region.name });
  }

  const stateMeta = new Map<string, { name: string; region: string }>();
  stateMeta.set(UNKNOWN_STATE.code, { name: UNKNOWN_STATE.name, region: UNKNOWN_REGION.code });
  for (const state of geography?.states ?? []) {
    stateMeta.set(state.state_fips, {
      name: state.name,
      region: state.census_region_code ?? UNKNOWN_REGION.code,
    });
  }

  type PlaceAcc = MindMapPlaceNode;
  type StateAcc = Omit<MindMapStateNode, "places"> & { places: Map<string, PlaceAcc> };
  type RegionAcc = Omit<MindMapRegionNode, "states"> & { states: Map<string, StateAcc> };

  const regions = new Map<string, RegionAcc>();
  const statusCounts = new Map<NationalStatus, number>();
  const ownerCounts = new Map<string, number>();

  const ensureRegion = (code: string, name: string): RegionAcc => {
    const existing = regions.get(code);
    if (existing) return existing;
    const created: RegionAcc = { code, name, projectCount: 0, locatedCount: 0, states: new Map() };
    regions.set(code, created);
    return created;
  };

  for (const project of included) {
    const stateCode = project.states[0] ?? UNKNOWN_STATE.code;
    const meta = stateMeta.get(stateCode) ?? { name: `State ${stateCode}`, region: UNKNOWN_REGION.code };
    const regionCode = meta.region;
    const regionName = regionMeta.get(regionCode)?.name ?? `Region ${regionCode}`;
    const region = ensureRegion(regionCode, regionName);
    let state = region.states.get(stateCode);
    if (!state) {
      state = { code: stateCode, name: meta.name, projectCount: 0, locatedCount: 0, places: new Map() };
      region.states.set(stateCode, state);
    }
    const placeInfo = placeFor(project, geography);
    let place = state.places.get(placeInfo.id);
    if (!place) {
      place = {
        id: placeInfo.id,
        label: placeInfo.label,
        kind: placeInfo.kind,
        projectCount: 0,
        locatedCount: 0,
        projects: [],
      };
      state.places.set(placeInfo.id, place);
    }
    const item = leaf(project);
    place.projects.push(item);
    place.projectCount += 1;
    state.projectCount += 1;
    region.projectCount += 1;
    if (item.located) {
      place.locatedCount += 1;
      state.locatedCount += 1;
      region.locatedCount += 1;
    }
    statusCounts.set(project.status_group, (statusCounts.get(project.status_group) ?? 0) + 1);
    const ownerKey = project.owner?.trim() || "Owner not reported";
    ownerCounts.set(ownerKey, (ownerCounts.get(ownerKey) ?? 0) + 1);
  }

  const regionNodes: MindMapRegionNode[] = sortByCountThenName(
    [...regions.values()].map((region) => ({
      code: region.code,
      name: region.name,
      projectCount: region.projectCount,
      locatedCount: region.locatedCount,
      states: sortByCountThenName(
        [...region.states.values()].map((state) => ({
          code: state.code,
          name: state.name,
          projectCount: state.projectCount,
          locatedCount: state.locatedCount,
          places: sortByCountThenName(
            [...state.places.values()].map((place) => ({
              ...place,
              projects: [...place.projects].sort((a, b) => a.name.localeCompare(b.name)),
            })),
          ),
        })),
      ),
    })),
  );

  const byRegion = sortByCountThenName(
    regionNodes.map((region) => ({ key: region.code, label: region.name, count: region.projectCount })),
  );
  const byStatus = sortByCountThenName(
    [...statusCounts.entries()].map(([key, count]) => ({
      key,
      label: STATUS_LABEL[key],
      count,
    })),
  );
  const byOwner = sortByCountThenName(
    [...ownerCounts.entries()].map(([label, count]) => ({ key: label, label, count })),
  ).slice(0, 8);

  return {
    regions: regionNodes,
    charts: { byRegion, byStatus, byOwner },
    meta: {
      total: projects.length,
      included: included.length,
      truncated,
      limit,
      notes: [
        "Hierarchy uses reported project geography only. Census boundaries never invent a place.",
        "Place labels prefer reviewed facility names, then county, then Unknown place.",
        "Electrical leaves are imported transmission project records, not inferred assets.",
      ],
    },
  };
}
