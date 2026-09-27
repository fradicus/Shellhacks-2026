import { z } from "zod";
import {
  SCHEMA_VERSION,
  PointSchema,
  type Envelope,
  type Point,
  type WaterData,
  type RiverGauge,
  type TideStationSummary,
  type FloodZone,
  type WetlandHit,
} from "./contracts";
import { digest, type Transport } from "./transport";

/** Free public hosts only — no paid keys. */
export const WATER_SOURCES = {
  usgs: "https://waterservices.usgs.gov/nwis/iv/",
  noaa_stations: "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json",
  noaa_tides: "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter",
  fema: "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query",
  wetlands: "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0/query",
} as const;

const MILES_PER_KM = 0.621371;
const GAUGE_RADIUS_MI = 17;
const TIDE_RADIUS_MI = 25;
const MAX_GAUGES = 3;

export type WaterContext = { io: Transport; now: Date };

function emptyWater(request: Point, reason: string, status: Envelope<WaterData>["status"] = "unavailable", now = new Date()): Envelope<WaterData> {
  return {
    schema_version: SCHEMA_VERSION,
    provider: "water",
    status,
    request_hash: digest(request),
    retrieved_at: now.toISOString(),
    source_updated_at: null,
    valid_from: null,
    valid_to: null,
    source_url: WATER_SOURCES.usgs,
    source_version: null,
    evidence_hash: null,
    coverage: { requested: 4, completed: 0, failed: 4, truncated: false },
    data: null,
    limitations: [reason],
  };
}

const fail = (error: unknown) => (error instanceof Error ? error.message.slice(0, 200) : "Provider unavailable");
const clean = (part: string, error: unknown) => `${part}: ${fail(error).replace(/https?:\/\/\S+/g, "[provider URL]")}`;

export function distanceMiles(a: Point, b: Point): number {
  const r = Math.PI / 180;
  const h = Math.sin(((a.lat - b.lat) * r) / 2) ** 2
    + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((a.lon - b.lon) * r) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h))) * MILES_PER_KM;
}

function bboxForMiles(point: Point, miles: number): { west: number; south: number; east: number; north: number } {
  const dLat = miles / 69;
  const dLon = miles / (69 * Math.max(0.2, Math.cos((point.lat * Math.PI) / 180)));
  return {
    west: Number((point.lon - dLon).toFixed(5)),
    south: Number((point.lat - dLat).toFixed(5)),
    east: Number((point.lon + dLon).toFixed(5)),
    north: Number((point.lat + dLat).toFixed(5)),
  };
}

const UsgsIv = z.object({
  value: z.object({
    timeSeries: z.array(z.object({
      sourceInfo: z.object({
        siteName: z.string(),
        siteCode: z.array(z.object({ value: z.string() })).min(1),
        geoLocation: z.object({
          geogLocation: z.object({ latitude: z.number().finite(), longitude: z.number().finite() }),
        }),
      }),
      variable: z.object({
        variableCode: z.array(z.object({ value: z.string() })).min(1),
        variableName: z.string().optional(),
        unit: z.object({ unitCode: z.string().optional() }).optional(),
      }),
      values: z.array(z.object({
        value: z.array(z.object({
          value: z.string(),
          dateTime: z.string(),
        })).max(500),
      })).min(1),
    })).max(500),
  }),
});

async function riverLevels(point: Point, ctx: WaterContext): Promise<{ part: WaterData["rivers"]; hash: string | null; limitation: string | null; status: Envelope<WaterData>["status"] }> {
  const box = bboxForMiles(point, GAUGE_RADIUS_MI);
  const url = `${WATER_SOURCES.usgs}?format=json&bBox=${box.west},${box.south},${box.east},${box.north}&parameterCd=00065&siteStatus=active`;
  try {
    const response = await ctx.io(url, {}, 1_500_000);
    const series = UsgsIv.parse(response.value).value.timeSeries;
    const gauges: RiverGauge[] = [];
    for (const item of series) {
      const site = item.sourceInfo;
      const reading = item.values[0]?.value.at(-1);
      if (!reading) continue;
      const location = { lat: site.geoLocation.geogLocation.latitude, lon: site.geoLocation.geogLocation.longitude };
      const miles = distanceMiles(point, location);
      if (miles > GAUGE_RADIUS_MI) continue;
      const height = Number(reading.value);
      gauges.push({
        site_id: site.siteCode[0].value,
        name: site.siteName,
        lat: location.lat,
        lon: location.lon,
        distance_mi: Number(miles.toFixed(2)),
        parameter: item.variable.variableCode[0].value,
        parameter_name: item.variable.variableName ?? "Gage height",
        unit: item.variable.unit?.unitCode ?? "ft",
        value: Number.isFinite(height) ? height : null,
        observed_at: reading.dateTime,
      });
    }
    gauges.sort((a, b) => a.distance_mi - b.distance_mi || a.site_id.localeCompare(b.site_id));
    const closest = gauges.slice(0, MAX_GAUGES);
    return {
      part: {
        search_radius_mi: GAUGE_RADIUS_MI,
        gauges: closest,
        scope: "USGS instantaneous gage height (00065) within ~17 mi; latest reading per site, usually ~15-minute reporting",
      },
      hash: response.hash,
      limitation: closest.length ? null : "No active USGS gage-height sites within 17 miles.",
      status: closest.length ? (gauges.length > MAX_GAUGES ? "partial" : "available") : "out_of_coverage",
    };
  } catch (error) {
    return { part: null, hash: null, limitation: clean("usgs", error), status: "unavailable" };
  }
}

const NoaaStations = z.object({
  stations: z.array(z.object({
    id: z.string(),
    name: z.string(),
    lat: z.number().finite(),
    lng: z.number().finite(),
    state: z.string().optional(),
    tidal: z.boolean().optional(),
  })).max(5000),
});

const NoaaPredictions = z.object({
  predictions: z.array(z.object({
    t: z.string(),
    v: z.string(),
    type: z.enum(["H", "L"]),
  })).max(50).optional(),
  error: z.object({ message: z.string() }).optional(),
});

function ymd(date: Date): string {
  return date.toISOString().slice(0, 10).replaceAll("-", "");
}

async function tides(point: Point, ctx: WaterContext): Promise<{ part: WaterData["tides"]; hash: string | null; limitation: string | null; status: Envelope<WaterData>["status"] }> {
  try {
    const list = await ctx.io(`${WATER_SOURCES.noaa_stations}?type=waterlevels`, {}, 1_500_000);
    const stations = NoaaStations.parse(list.value).stations
      .map((station) => ({
        id: station.id,
        name: station.name,
        lat: station.lat,
        lon: station.lng,
        state: station.state ?? null,
        distance_mi: Number(distanceMiles(point, { lat: station.lat, lon: station.lng }).toFixed(2)),
      }))
      .filter((station) => station.distance_mi <= TIDE_RADIUS_MI)
      .sort((a, b) => a.distance_mi - b.distance_mi || a.id.localeCompare(b.id));
    if (!stations.length) {
      return {
        part: {
          search_radius_mi: TIDE_RADIUS_MI,
          station: null,
          highs_lows: [],
          scope: "NOAA CO-OPS water-level stations; tides omitted when no station is within 25 mi (treated as inland)",
        },
        hash: list.hash,
        limitation: "No NOAA water-level station within 25 miles; tides skipped (likely inland).",
        status: "out_of_coverage",
      };
    }
    const nearest = stations[0]!;
    const day = ymd(ctx.now);
    const next = ymd(new Date(ctx.now.getTime() + 86400_000));
    const predUrl = `${WATER_SOURCES.noaa_tides}?product=predictions&application=GridBridge&begin_date=${day}&end_date=${next}&datum=MLLW&station=${encodeURIComponent(nearest.id)}&time_zone=gmt&interval=hilo&units=english&format=json`;
    const pred = await ctx.io(predUrl);
    const parsed = NoaaPredictions.parse(pred.value);
    if (parsed.error?.message) throw new Error(parsed.error.message);
    const highsLows = (parsed.predictions ?? []).map((row) => {
      const value = Number(row.v);
      return {
        time: row.t.includes("T") ? `${row.t.replace(" ", "T")}Z` : `${row.t.replace(" ", "T")}:00Z`,
        value_ft: Number.isFinite(value) ? value : null,
        type: row.type === "H" ? "high" as const : "low" as const,
      };
    });
    const station: TideStationSummary = {
      id: nearest.id,
      name: nearest.name,
      lat: nearest.lat,
      lon: nearest.lon,
      state: nearest.state,
      distance_mi: nearest.distance_mi,
    };
    return {
      part: {
        search_radius_mi: TIDE_RADIUS_MI,
        station,
        highs_lows: highsLows,
        scope: "Nearest NOAA CO-OPS station within 25 mi; high/low predictions for the request day (GMT, MLLW feet)",
      },
      hash: digest([list.hash, pred.hash]),
      limitation: highsLows.length ? null : "Tide station found but no high/low predictions for the request day.",
      status: highsLows.length ? "available" : "partial",
    };
  } catch (error) {
    return { part: null, hash: null, limitation: clean("noaa_tides", error), status: "unavailable" };
  }
}

const FemaQuery = z.object({
  features: z.array(z.object({
    attributes: z.object({
      FLD_ZONE: z.string().nullable().optional(),
      ZONE_SUBTY: z.string().nullable().optional(),
      SFHA_TF: z.string().nullable().optional(),
    }),
  })).max(20),
});

async function floodZone(point: Point, ctx: WaterContext): Promise<{ part: WaterData["flood"]; hash: string | null; limitation: string | null; status: Envelope<WaterData>["status"] }> {
  const url = `${WATER_SOURCES.fema}?geometry=${point.lon},${point.lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=FLD_ZONE,ZONE_SUBTY,SFHA_TF&returnGeometry=false&f=json`;
  try {
    const response = await ctx.io(url);
    const features = FemaQuery.parse(response.value).features;
    if (!features.length) {
      return {
        part: { zones: [], scope: "FEMA NFHL flood hazard zones (layer 28) at point; absence is not proof of no flood risk" },
        hash: response.hash,
        limitation: "No FEMA flood-hazard polygon returned for this point.",
        status: "out_of_coverage",
      };
    }
    const zones: FloodZone[] = features.map((feature) => ({
      zone: feature.attributes.FLD_ZONE ?? null,
      subtype: feature.attributes.ZONE_SUBTY ?? null,
      special_flood_hazard_area: feature.attributes.SFHA_TF === "T" ? true : feature.attributes.SFHA_TF === "F" ? false : null,
    }));
    return {
      part: { zones, scope: "FEMA NFHL layer 28 flood hazard zone at the clicked point; not a permit determination" },
      hash: response.hash,
      limitation: null,
      status: "available",
    };
  } catch (error) {
    return { part: null, hash: null, limitation: clean("fema", error), status: "unavailable" };
  }
}

const WetlandsQuery = z.object({
  features: z.array(z.object({
    attributes: z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()])),
  })).max(20),
  error: z.object({ message: z.string() }).optional(),
});

function attr(row: Record<string, string | number | boolean | null>, keys: string[]): string | null {
  for (const key of keys) {
    const value = row[key] ?? row[`Wetlands.${key}`];
    if (value == null || value === "") continue;
    return String(value);
  }
  return null;
}

async function wetlands(point: Point, ctx: WaterContext): Promise<{ part: WaterData["wetlands"]; hash: string | null; limitation: string | null; status: Envelope<WaterData>["status"] }> {
  const url = `${WATER_SOURCES.wetlands}?geometry=${point.lon},${point.lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json`;
  try {
    const response = await ctx.io(url, {}, 1_000_000);
    const parsed = WetlandsQuery.parse(response.value);
    if (parsed.error?.message) throw new Error(parsed.error.message);
    const hits: WetlandHit[] = parsed.features.map((feature) => ({
      wetland_type: attr(feature.attributes, ["WETLAND_TYPE", "Wetland_Type"]),
      attribute: attr(feature.attributes, ["ATTRIBUTE", "Attribute"]),
      acres: (() => {
        const raw = attr(feature.attributes, ["ACRES", "Acres"]);
        if (raw == null) return null;
        const value = Number(raw);
        return Number.isFinite(value) ? value : null;
      })(),
    }));
    return {
      part: {
        mapped: hits.length > 0,
        features: hits,
        scope: "USFWS National Wetlands Inventory point intersection; mapped absence is not a jurisdictional determination",
      },
      hash: response.hash,
      limitation: hits.length ? null : "Point is not inside a mapped NWI wetland polygon.",
      status: "available",
    };
  } catch (error) {
    return { part: null, hash: null, limitation: clean("wetlands", error), status: "unavailable" };
  }
}

/** Combined free public water context for a clicked point. */
export async function water(point: Point, ctx: WaterContext): Promise<Envelope<WaterData>> {
  const result = emptyWater(point, "Public USGS / NOAA / FEMA / USFWS water context; not a flood or wetland determination.", "available", ctx.now);
  try {
    PointSchema.parse(point);
    const [rivers, tide, flood, wetland] = await Promise.all([
      riverLevels(point, ctx),
      tides(point, ctx),
      floodZone(point, ctx),
      wetlands(point, ctx),
    ]);
    const parts = [rivers, tide, flood, wetland];
    const completed = parts.filter((part) => part.part !== null).length;
    const hashes = parts.map((part) => part.hash).filter((hash): hash is string => !!hash);
    result.coverage = { requested: 4, completed, failed: 4 - completed, truncated: false };
    result.evidence_hash = hashes.length ? digest(hashes) : null;
    result.limitations = [
      "Water evidence does not certify safe access, flood insurance requirements or wetland jurisdiction.",
      ...parts.map((part) => part.limitation).filter((item): item is string => !!item),
    ];
    result.source_url = WATER_SOURCES.usgs;
    if (!completed) {
      result.status = "unavailable";
      result.data = null;
      return result;
    }
    result.data = {
      rivers: rivers.part,
      tides: tide.part,
      flood: flood.part,
      wetlands: wetland.part,
      scope: "Independent free public water sources around a clicked point; each source can fail without inventing coverage",
    };
    const statuses = parts.map((part) => part.status);
    if (statuses.every((status) => status === "available")) result.status = "available";
    else result.status = "partial";
    return result;
  } catch (error) {
    return emptyWater(point, clean("water", error), "unavailable", ctx.now);
  }
}
