import { z } from "zod";

/**
 * Only the fields the Site factors tab reads from /api/operations/site and /api/operations/water. Objects are not
 * strict so additive provider fields never break this tab; anything missing stays null and is shown as unknown.
 */
const num = z.number().finite().nullable();
const Horizon = z.object({ depth_top_cm: num, depth_bottom_cm: num, ph_h2o_1_to_1: num });
const Component = z.object({ name: z.string().nullable(), percent: num, drainage_class: z.string().nullable(), hydrologic_group: z.string().nullable(), horizons: z.array(Horizon).optional() });
export const SoilSchema = z.object({ status: z.string(), limitations: z.array(z.string()), data: z.object({ map_units: z.array(z.object({ name: z.string(), components: z.array(Component) })) }).nullable() });
const WeatherSchema = z.object({ status: z.string(), data: z.object({ samples: z.array(z.object({ alerts: z.array(z.object({ event: z.string() })) })) }).nullable() });
export const SiteSchema = z.object({ soil: SoilSchema, weather: WeatherSchema });

const Gauge = z.object({ site_id: z.string(), name: z.string(), lat: z.number().finite(), lon: z.number().finite(), distance_mi: z.number().finite(), parameter_name: z.string(), unit: z.string(), value: num, observed_at: z.string() });
const Tides = z.object({ search_radius_mi: z.number(), station: z.object({ id: z.string(), name: z.string(), lat: z.number().finite(), lon: z.number().finite(), distance_mi: z.number().finite() }).nullable(), highs_lows: z.array(z.object({ time: z.string(), value_ft: num, type: z.enum(["high", "low"]) })) });
export const WaterSchema = z.object({ water: z.object({
  status: z.string(), limitations: z.array(z.string()), retrieved_at: z.string(),
  data: z.object({
    rivers: z.object({ search_radius_mi: z.number(), gauges: z.array(Gauge) }).nullable(),
    tides: Tides.nullable(),
    flood: z.object({ zones: z.array(z.object({ zone: z.string().nullable(), subtype: z.string().nullable(), special_flood_hazard_area: z.boolean().nullable() })) }).nullable(),
    wetlands: z.object({ mapped: z.boolean(), features: z.array(z.object({ wetland_type: z.string().nullable(), attribute: z.string().nullable(), acres: num })) }).nullable(),
  }).nullable(),
}) });
const StationRef = z.object({ id: z.string(), name: z.string(), distance_mi: z.number().finite().nonnegative(), source_url: z.string().url() });
const DailySeries = z.array(num).min(365).max(4000);
/** /api/weather-history: committed NOAA station series; null history = no analyzed station within range. */
export const HistorySchema = z.object({ history: z.object({
  window: z.object({ start: z.string().regex(/^\d{4}-\d{2}-\d{2}$/), end: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) }),
  citation: z.string().url(), rain: StationRef, wind: StationRef.nullable(),
  prcp_in: DailySeries, tmax_f: DailySeries, wsf2_mph: DailySeries.nullable(),
}).refine((h) => h.prcp_in.length === h.tmax_f.length && (!h.wsf2_mph || h.wsf2_mph.length === h.prcp_in.length), "Series lengths differ").nullable() });
export type SiteEvidenceData = z.infer<typeof SiteSchema>;
export type WaterEvidence = z.infer<typeof WaterSchema>["water"];
type SoilData = NonNullable<z.infer<typeof SoilSchema>["data"]>;

export const PH_DEPTH_CM = { top: 0, bottom: 30 } as const;

/**
 * Representative horizon pH over 0–30 cm, weighted by component percent × overlap thickness. pH is logarithmic, so
 * this is a comparison index, not a chemical average. Missing pH, depth or component percent is skipped, never zero.
 */
export function soilPhSummary(data: SoilData | null, top: number = PH_DEPTH_CM.top, bottom: number = PH_DEPTH_CM.bottom) {
  let weight = 0, sum = 0, used = 0;
  for (const unit of data?.map_units ?? []) for (const component of unit.components) {
    if (component.percent == null || component.percent <= 0) continue;
    for (const h of component.horizons ?? []) {
      if (h.ph_h2o_1_to_1 == null || h.depth_top_cm == null || h.depth_bottom_cm == null) continue;
      const overlap = Math.min(h.depth_bottom_cm, bottom) - Math.max(h.depth_top_cm, top);
      if (overlap <= 0) continue;
      weight += overlap * component.percent; sum += overlap * component.percent * h.ph_h2o_1_to_1; used++;
    }
  }
  return { value: weight > 0 ? Math.round((sum / weight) * 10) / 10 : null, horizonsUsed: used };
}

/** Plain-text facts the user may copy into the multiplier basis. They are citations, never inputs to the math. */
export function evidenceLines(site: SiteEvidenceData | null, water: WaterEvidence | null): string[] {
  const lines: string[] = [];
  const w = water?.data;
  if (w?.flood) {
    const zone = w.flood.zones[0];
    lines.push(zone ? `FEMA NFHL zone ${zone.zone ?? "unknown"}${zone.special_flood_hazard_area ? " (SFHA)" : ""}` : "FEMA flood zone unknown (no mapped polygon)");
  }
  if (w?.wetlands) {
    const f = w.wetlands.features[0];
    lines.push(w.wetlands.mapped && f ? `NWI wetland mapped: ${f.wetland_type ?? "type n/a"}${f.attribute ? ` ${f.attribute}` : ""}` : "No NWI wetland polygon at point");
  }
  const ph = soilPhSummary(site?.soil.data ?? null);
  if (ph.value !== null) lines.push(`SSURGO pH ${ph.value.toFixed(1)} (0–30 cm estimate)`);
  const component = site?.soil.data?.map_units[0]?.components.slice().sort((a, b) => (b.percent ?? 0) - (a.percent ?? 0))[0];
  if (component?.drainage_class) lines.push(`Soil: ${component.name ?? "component"}, ${component.drainage_class}${component.hydrologic_group ? `, HSG ${component.hydrologic_group}` : ""}`);
  const heights = (w?.tides?.highs_lows ?? []).flatMap((e) => (e.value_ft === null ? [] : [e.value_ft]));
  if (w?.tides?.station && heights.length > 1) lines.push(`Tidal site: ${w.tides.station.name}, predicted range ${(Math.max(...heights) - Math.min(...heights)).toFixed(1)} ft`);
  const alerts = site?.weather.data?.samples.flatMap((sample) => sample.alerts) ?? [];
  if (alerts.length) lines.push(`NWS alerts active: ${[...new Set(alerts.map((a) => a.event))].join(", ")}`);
  return lines;
}
