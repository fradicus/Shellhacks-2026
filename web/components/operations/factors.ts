/**
 * Route-factors pipeline: derive evidence-backed delay/cost factors from F34
 * site + route envelopes, then apply only explicit user rate assumptions.
 * Never invent minutes or dollars; blanks stay null.
 */

import type {
  AEFData,
  Envelope,
  RoadworkData,
  RouteData,
  RouteResponse,
  SiteResponse,
  SoilData,
  WeatherData,
} from "../../lib/operations/contracts";

export const FACTOR_KINDS = [
  "travel_baseline",
  "weather_alert",
  "precipitation",
  "roadwork",
  "route_restriction",
  "route_warning",
  "soil_drainage",
  "aef_coverage",
] as const;

export type FactorKind = (typeof FACTOR_KINDS)[number];
export type FactorPresence = "present" | "absent" | "unknown" | "unavailable";
export type FactorImpact = "time" | "cost" | "both" | "none";

export type FactorEvidence = {
  id: string;
  kind: FactorKind;
  label: string;
  presence: FactorPresence;
  impact: FactorImpact;
  evidence: string;
  source: string;
  provider_status: string | null;
  /** Provider-reported travel minutes when present; otherwise null. Never invented. */
  known_time_minutes: number | null;
};

export type FactorRateInput = {
  time_minutes: string;
  cost_usd: string;
};

export type AppliedFactor = FactorEvidence & {
  time_minutes_add: number | null;
  cost_cents_add: number | null;
  time_error: string | null;
  cost_error: string | null;
};

export type FactorTotals = {
  time_minutes: number | null;
  cost_cents: number | null;
  present_count: number;
  rated_time_count: number;
  rated_cost_count: number;
  has_errors: boolean;
};

export type RouteFactorsInput = {
  site: SiteResponse | null;
  route: RouteResponse | null;
  weather: Envelope<WeatherData> | null;
  roadwork: Envelope<RoadworkData> | null;
};

function minutes(seconds: number | null | undefined): number | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  return Math.round(seconds / 60);
}

function weatherAlerts(envelope: Envelope<WeatherData> | null): { count: number; names: string[]; status: string | null } {
  if (!envelope) return { count: 0, names: [], status: null };
  if (!envelope.data) return { count: 0, names: [], status: envelope.status };
  const alerts = envelope.data.samples.flatMap((sample) => sample.alerts);
  return { count: alerts.length, names: alerts.slice(0, 3).map((alert) => alert.event), status: envelope.status };
}

function precipMax(envelope: Envelope<WeatherData> | null): { max: number | null; status: string | null } {
  if (!envelope) return { max: null, status: null };
  if (!envelope.data) return { max: null, status: envelope.status };
  const values = envelope.data.samples
    .flatMap((sample) => sample.forecast)
    .map((period) => period.precipitation_probability)
    .filter((value): value is number => value != null && Number.isFinite(value));
  return { max: values.length ? Math.max(...values) : null, status: envelope.status };
}

function roadworkEvents(envelope: Envelope<RoadworkData> | null): { count: number; names: string[]; status: string | null } {
  if (!envelope) return { count: 0, names: [], status: null };
  if (!envelope.data) return { count: 0, names: [], status: envelope.status };
  const events = envelope.data.events;
  return {
    count: events.length,
    names: events.slice(0, 3).map((event) => event.road_names.join(", ") || "Unnamed road event"),
    status: envelope.status,
  };
}

function drainageClasses(envelope: Envelope<SoilData> | null): { classes: string[]; status: string | null } {
  if (!envelope) return { classes: [], status: null };
  if (!envelope.data) return { classes: [], status: envelope.status };
  const classes = [
    ...new Set(
      envelope.data.map_units
        .flatMap((unit) => unit.components)
        .map((component) => component.drainage_class)
        .filter((value): value is string => !!value),
    ),
  ];
  return { classes, status: envelope.status };
}

function aefSample(envelope: Envelope<AEFData> | null): { year: number | null; status: string | null } {
  if (!envelope) return { year: null, status: null };
  const sample = envelope.data?.samples[0];
  return { year: sample?.year ?? null, status: envelope.status };
}

/** Pure derive step: evidence → factor rows. No rates, no invented quantities. */
export function deriveRouteFactors(input: RouteFactorsInput): FactorEvidence[] {
  const factors: FactorEvidence[] = [];
  const routeEnvelope = input.route?.route ?? null;
  const routeData: RouteData | null = routeEnvelope?.data ?? null;
  const travelMinutes = minutes(routeData?.travel_seconds);

  factors.push({
    id: "travel_baseline",
    kind: "travel_baseline",
    label: "Baseline truck travel",
    presence: routeData ? "present" : routeEnvelope ? "unavailable" : "unknown",
    impact: "both",
    evidence: routeData
      ? `${(routeData.distance_m / 1609.344).toFixed(1)} mi · ${travelMinutes} min provider travel time (not construction duration)`
      : input.route
        ? routeEnvelope?.limitations[0] ?? "Truck route unavailable."
        : "Check a truck route on the Planning tab to attach baseline travel time.",
    source: routeEnvelope?.source_url ?? "Google Routes (when configured)",
    provider_status: routeEnvelope?.status ?? null,
    known_time_minutes: travelMinutes,
  });

  const alerts = weatherAlerts(input.weather ?? input.route?.weather ?? null);
  factors.push({
    id: "weather_alert",
    kind: "weather_alert",
    label: "Active weather alerts",
    presence: !alerts.status ? "unknown" : alerts.status === "unavailable" || alerts.status === "not_configured" || alerts.status === "deferred"
      ? "unavailable"
      : alerts.count > 0
        ? "present"
        : "absent",
    impact: "both",
    evidence: !alerts.status
      ? "Check a worksite to load current weather evidence."
      : alerts.count > 0
        ? `${alerts.count} alert${alerts.count === 1 ? "" : "s"}: ${alerts.names.join("; ")}${alerts.count > 3 ? "…" : ""}`
        : "No active alerts returned for the sampled point.",
    source: "NWS api.weather.gov",
    provider_status: alerts.status,
    known_time_minutes: null,
  });

  const precip = precipMax(input.weather ?? input.route?.weather ?? null);
  factors.push({
    id: "precipitation",
    kind: "precipitation",
    label: "Forecast precipitation",
    presence: !precip.status
      ? "unknown"
      : precip.status === "unavailable" || precip.status === "not_configured" || precip.status === "deferred"
        ? "unavailable"
        : precip.max == null
          ? "unknown"
          : precip.max >= 50
            ? "present"
            : "absent",
    impact: "time",
    evidence: !precip.status
      ? "Check a worksite to load forecast evidence."
      : precip.max == null
        ? "Precipitation probability not published in the returned forecast periods."
        : `Highest returned precip probability ${precip.max}% across shown forecast periods.`,
    source: "NWS forecast",
    provider_status: precip.status,
    known_time_minutes: null,
  });

  const work = roadworkEvents(input.roadwork ?? input.route?.roadwork ?? null);
  factors.push({
    id: "roadwork",
    kind: "roadwork",
    label: "Nearby road work",
    presence: !work.status
      ? "unknown"
      : work.status === "unavailable" || work.status === "out_of_coverage" || work.status === "not_configured" || work.status === "deferred"
        ? "unavailable"
        : work.count > 0
          ? "present"
          : "absent",
    impact: "both",
    evidence: !work.status
      ? "Check a worksite to load road-work evidence."
      : work.count > 0
        ? `${work.count} event${work.count === 1 ? "" : "s"}: ${work.names.join("; ")}${work.count > 3 ? "…" : ""}`
        : "No nearby work-zone events returned for the sampled coverage.",
    source: "WZDx / published work-zone feeds",
    provider_status: work.status,
    known_time_minutes: null,
  });

  const ignored = routeData?.restrictions_partially_ignored;
  factors.push({
    id: "route_restriction",
    kind: "route_restriction",
    label: "Vehicle restrictions partially ignored",
    presence: routeData ? (ignored ? "present" : "absent") : input.route ? "unavailable" : "unknown",
    impact: "both",
    evidence: routeData
      ? ignored
        ? "Provider returned a best-effort route that ignored some vehicle restrictions."
        : "Provider did not flag ignored vehicle restrictions (not a safety guarantee)."
      : "Requires a completed truck route assessment.",
    source: "Google TRUCK routing advisory",
    provider_status: routeEnvelope?.status ?? null,
    known_time_minutes: null,
  });

  const warnings = routeData?.warnings ?? [];
  factors.push({
    id: "route_warning",
    kind: "route_warning",
    label: "Provider route warnings",
    presence: routeData ? (warnings.length ? "present" : "absent") : input.route ? "unavailable" : "unknown",
    impact: "time",
    evidence: routeData
      ? warnings.length
        ? warnings.slice(0, 3).join("; ")
        : "No provider warnings returned with the route."
      : "Requires a completed truck route assessment.",
    source: "Google Routes warnings",
    provider_status: routeEnvelope?.status ?? null,
    known_time_minutes: null,
  });

  const soil = drainageClasses(input.site?.soil ?? null);
  const wet = soil.classes.some((value) => /poor|very poorly|somewhat poorly/i.test(value));
  factors.push({
    id: "soil_drainage",
    kind: "soil_drainage",
    label: "Mapped soil drainage",
    presence: !soil.status
      ? "unknown"
      : soil.status === "unavailable" || soil.status === "out_of_coverage" || soil.status === "not_configured"
        ? "unavailable"
        : soil.classes.length === 0
          ? "unknown"
          : wet
            ? "present"
            : "absent",
    impact: "cost",
    evidence: !soil.status
      ? "Check a worksite to load soil survey context."
      : soil.classes.length
        ? `Mapped drainage classes: ${soil.classes.join(", ")}. Survey context only — not a field geotechnical opinion.`
        : "Soil map units returned without published drainage classes.",
    source: "USDA SSURGO / Soil Data Access",
    provider_status: soil.status,
    known_time_minutes: null,
  });

  const aef = aefSample(input.site?.aef ?? input.route?.aef ?? null);
  factors.push({
    id: "aef_coverage",
    kind: "aef_coverage",
    label: "Annual AEF coverage",
    presence: !aef.status
      ? "unknown"
      : aef.year != null
        ? "present"
        : aef.status === "unavailable" || aef.status === "out_of_coverage" || aef.status === "not_configured"
          ? "unavailable"
          : "unknown",
    impact: "none",
    evidence: aef.year != null
      ? `Exact evidenced annual embedding year ${aef.year} at the requested point. Annual context only — not live weather or soil strength.`
      : aef.status
        ? "No exact evidenced point/year AEF sample matched this worksite."
        : "Check a worksite with an AEF year to load annual reference evidence.",
    source: "Google AlphaEarth Foundations",
    provider_status: aef.status,
    known_time_minutes: null,
  });

  return factors;
}

export function rateError(value: string, money: boolean): string | null {
  if (!value.trim()) return null;
  const format = money ? /^\d+(\.\d{1,2})?$/ : /^\d+$/;
  if (!format.test(value.trim())) {
    return money ? "Enter a nonnegative USD amount with up to 2 decimals." : "Enter a nonnegative whole number of minutes.";
  }
  if (Number(value) > (money ? 1_000_000_000 : 100_000)) return "Amount is too large for this worksheet.";
  return null;
}

/** Apply only explicit user rates. Known provider travel minutes seed the baseline when the user leaves time blank. */
export function applyFactorRates(
  factors: FactorEvidence[],
  rates: Record<string, FactorRateInput>,
  options: { seedKnownTravelTime?: boolean } = { seedKnownTravelTime: true },
): { factors: AppliedFactor[]; totals: FactorTotals } {
  let timeSum = 0;
  let costSum = 0;
  let timeKnown = true;
  let costKnown = true;
  let ratedTime = 0;
  let ratedCost = 0;
  let hasErrors = false;
  let anyTime = false;
  let anyCost = false;

  const applied = factors.map((factor) => {
    const rate = rates[factor.id] ?? { time_minutes: "", cost_usd: "" };
    const timeError = rateError(rate.time_minutes, false);
    const costError = rateError(rate.cost_usd, true);
    if (timeError || costError) hasErrors = true;

    let time_minutes_add: number | null = null;
    if (!timeError && rate.time_minutes.trim()) {
      time_minutes_add = Number(rate.time_minutes);
      ratedTime += 1;
    } else if (
      options.seedKnownTravelTime
      && factor.kind === "travel_baseline"
      && factor.known_time_minutes != null
      && !rate.time_minutes.trim()
    ) {
      time_minutes_add = factor.known_time_minutes;
    }

    let cost_cents_add: number | null = null;
    if (!costError && rate.cost_usd.trim()) {
      cost_cents_add = Math.round(Number(rate.cost_usd) * 100);
      ratedCost += 1;
    }

    const countsForTotals = factor.presence === "present" || factor.kind === "travel_baseline";
    const needsTime = countsForTotals && (factor.impact === "time" || factor.impact === "both" || factor.kind === "travel_baseline");
    const needsCost = countsForTotals && (factor.impact === "cost" || factor.impact === "both" || factor.kind === "travel_baseline");
    if (needsTime) {
      if (time_minutes_add == null) timeKnown = false;
      else {
        timeSum += time_minutes_add;
        anyTime = true;
      }
    }
    if (needsCost) {
      if (cost_cents_add == null) costKnown = false;
      else {
        costSum += cost_cents_add;
        anyCost = true;
      }
    }

    return { ...factor, time_minutes_add, cost_cents_add, time_error: timeError, cost_error: costError };
  });

  const present_count = factors.filter((factor) => factor.presence === "present").length;
  return {
    factors: applied,
    totals: {
      time_minutes: anyTime && timeKnown && !hasErrors ? timeSum : null,
      cost_cents: anyCost && costKnown && !hasErrors ? costSum : null,
      present_count,
      rated_time_count: ratedTime,
      rated_cost_count: ratedCost,
      has_errors: hasErrors,
    },
  };
}

export function money(cents: number): string {
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function emptyRates(factors: FactorEvidence[]): Record<string, FactorRateInput> {
  return Object.fromEntries(factors.map((factor) => [factor.id, { time_minutes: "", cost_usd: "" }]));
}
