import type { ReactNode } from "react";
import type { Envelope, WeatherData, RoadworkData, SoilData, AEFData, RouteData, RouteRequest } from "@/lib/operations/contracts";
import type { PredictionResponse } from "@/lib/outcomes/model";
import { providerLabel, statusTone } from "./logic";
import styles from "./operations.module.css";

export function formatTime(value: string | null): string {
  if (!value) return "Not published";
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : value;
}

function number(value: number, maximumFractionDigits = 1) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(value);
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`${styles.badge} ${styles[statusTone(status)]}`}>{status.replaceAll("_", " ")}</span>;
}

function EnvelopeFrame<T>({ envelope, title, children }: { envelope: Envelope<T>; title?: string; children?: ReactNode }) {
  return <article className={styles.evidenceCard} data-provider={envelope.provider}>
    <div className={styles.cardHeading}>
      <div><span className="eyebrow">{title ?? providerLabel(envelope.provider)}</span><h3>{providerLabel(envelope.provider)}</h3></div>
      <StatusBadge status={envelope.status} />
    </div>
    {children}
    <dl className={styles.metadata}>
      <div><dt>Retrieved</dt><dd>{formatTime(envelope.retrieved_at)}</dd></div>
      <div><dt>Source updated</dt><dd>{formatTime(envelope.source_updated_at)}</dd></div>
      <div><dt>Coverage</dt><dd>{envelope.coverage.completed}/{envelope.coverage.requested} completed{envelope.coverage.truncated ? ", truncated" : ""}</dd></div>
    </dl>
    <details className={styles.evidenceDetails}>
      <summary>Source and limitations</summary>
      <p><a href={envelope.source_url} target="_blank" rel="noreferrer">Open provider source</a></p>
      <p className={styles.hash}>Evidence {envelope.evidence_hash ?? "Not available"}</p>
      <ul>{envelope.limitations.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>
    </details>
  </article>;
}

export function WeatherPanel({ envelope, refreshFailed }: { envelope: Envelope<WeatherData>; refreshFailed?: string | null }) {
  const samples = envelope.data?.samples ?? [];
  const forecast = samples.flatMap((sample) => sample.forecast).slice(0, 4);
  const alerts = samples.flatMap((sample) => sample.alerts);
  return <EnvelopeFrame envelope={envelope} title="Current conditions">
    {refreshFailed && <p className={styles.inlineWarning}>Latest refresh failed: {refreshFailed}. Older evidence remains timestamped above.</p>}
    {!envelope.data ? <p className={styles.empty}>{envelope.limitations[0] ?? "Weather is unavailable."}</p> : <>
      <p className={styles.scope}>{envelope.data.scope}</p>
      <div className={styles.metricRow}>
        <div><strong>{alerts.length}</strong><span>active alerts returned</span></div>
        <div><strong>{forecast.length}</strong><span>forecast periods shown</span></div>
      </div>
      {alerts.length > 0 && <ul className={styles.eventList}>{alerts.slice(0, 3).map((alert) => <li key={alert.id}><strong>{alert.event}</strong><span>{alert.severity ?? "Severity not published"} · expires {formatTime(alert.expires)}</span></li>)}</ul>}
      {forecast.length > 0 && <ol className={styles.forecast}>{forecast.map((period) => <li key={`${period.start}-${period.end}`}>
        <time>{formatTime(period.start)}</time><strong>{period.temperature == null ? "Temperature unknown" : `${number(period.temperature)}°${period.temperature_unit ?? ""}`}</strong>
        <span>{period.description} · precip {period.precipitation_probability == null ? "unknown" : `${number(period.precipitation_probability)}%`} · wind {[period.wind_direction, period.wind_speed].filter(Boolean).join(" ") || "unknown"}</span>
      </li>)}</ol>}
      {alerts.length > 0 && <details className={styles.evidenceDetails}><summary>All {alerts.length} returned alerts</summary><ul>{alerts.map((alert) => <li key={alert.id}><strong>{alert.event}</strong> · {alert.severity ?? "severity unknown"} · expires {formatTime(alert.expires)}<br />{alert.description}</li>)}</ul></details>}
    </>}
  </EnvelopeFrame>;
}

export function RoadworkPanel({ envelope, refreshFailed }: { envelope: Envelope<RoadworkData>; refreshFailed?: string | null }) {
  const events = envelope.data?.events ?? [];
  return <EnvelopeFrame envelope={envelope} title="Current conditions">
    {refreshFailed && <p className={styles.inlineWarning}>Latest refresh failed: {refreshFailed}. Older evidence remains timestamped above.</p>}
    {!envelope.data ? <p className={styles.empty}>{envelope.limitations[0] ?? "Road-work evidence is unavailable."}</p> : <>
      <p className={styles.scope}>{envelope.data.scope}</p>
      <p className={styles.bigValue}>{events.length}<span>reported nearby events</span></p>
      {events.length > 0 && <ul className={styles.eventList}>{events.slice(0, 5).map((event) => <li key={event.id}>
        <strong>{event.road_names.join(", ") || "Road name not published"}</strong>
        <span>{event.vehicle_impact} · {formatTime(event.start)} to {formatTime(event.end)}</span>
      </li>)}</ul>}
      {events.length > 0 && <details className={styles.evidenceDetails}><summary>All {events.length} returned road-work events and restrictions</summary><ul>{events.map((event) => <li key={event.id}><strong>{event.road_names.join(", ") || "Road name not published"}</strong> · {event.vehicle_impact} · {formatTime(event.start)} to {formatTime(event.end)}<br />{event.description ?? "Description not published"}{event.restrictions.length ? <ul>{event.restrictions.map((restriction, index) => <li key={`${restriction.type}-${index}`}>{restriction.type}: {restriction.value ?? "value unknown"} {restriction.unit ?? ""}</li>)}</ul> : <span> · restrictions not published</span>}</li>)}</ul></details>}
    </>}
  </EnvelopeFrame>;
}

export function SoilPanel({ envelope }: { envelope: Envelope<SoilData> }) {
  const units = envelope.data?.map_units ?? [];
  return <EnvelopeFrame envelope={envelope} title="Reference evidence">
    {!envelope.data ? <p className={styles.empty}>{envelope.limitations[0] ?? "Soil survey context is unavailable."}</p> : <>
      <p className={styles.scope}>{envelope.data.scope}</p>
      <p className={styles.bigValue}>{units.length}<span>mapped soil units</span></p>
      <ul className={styles.eventList}>{units.slice(0, 4).map((unit) => <li key={unit.mukey}><strong>{unit.name}</strong><span>{unit.area_symbol} · {unit.components.length} components · survey {unit.survey_updated_at ?? "date unknown"}</span></li>)}</ul>
      {units.length > 0 && <details className={styles.evidenceDetails}><summary>All mapped units and component facts</summary>{units.map((unit) => <section key={unit.mukey}><h4>{unit.name} · {unit.mukey}</h4><ul>{unit.components.length ? unit.components.map((component) => <li key={component.cokey}>{component.name ?? "Component name unknown"} · {component.percent ?? "percent unknown"}% · drainage {component.drainage_class ?? "unknown"} · hydrologic group {component.hydrologic_group ?? "unknown"}</li>) : <li>No component facts published.</li>}</ul></section>)}</details>}
    </>}
  </EnvelopeFrame>;
}

export function AEFPanel({ envelope }: { envelope: Envelope<AEFData> }) {
  const sample = envelope.data?.samples[0];
  return <EnvelopeFrame envelope={envelope} title="Annual reference evidence">
    {!sample ? <p className={styles.empty}>{envelope.limitations.at(-1) ?? "No exact evidenced point/year artifact matches this worksite."}</p> : <>
      <p className={styles.scope}>Annual 64-dimension satellite embedding. It is not current weather, soil strength, or a site approval.</p>
      <div className={styles.metricRow}><div><strong>{sample.year}</strong><span>annual vintage</span></div><div><strong>{sample.pixel_size_m} m</strong><span>pixel size</span></div></div>
      <p className={styles.small}>{sample.crs} · row {sample.row}, column {sample.col}</p>
      <p className={styles.small}>{sample.attribution}</p>
      <details className={styles.evidenceDetails}><summary>Pixel identity</summary><p className={styles.hash}>Sample {sample.sample_sha256}</p><p className={styles.hash}>Index {sample.index_sha256}</p></details>
    </>}
  </EnvelopeFrame>;
}

export function RoutePanel({ envelope, request, limitations, outdated }: { envelope: Envelope<RouteData>; request: RouteRequest; limitations: string[]; outdated?: boolean }) {
  const route = envelope.data;
  return <EnvelopeFrame envelope={envelope} title="Truck route · route-only presentation">
    {outdated && <p className={styles.inlineWarning}>Inputs changed. This route remains visible as older evidence; run it again before use.</p>}
    {!route ? <p className={styles.empty}>{envelope.limitations[0] ?? "A truck route is unavailable."}</p> : <>
      <div className={styles.metricRow}>
        <div><strong>{number(route.distance_m / 1609.344, 1)} mi</strong><span>route distance</span></div>
        <div><strong>{number(route.travel_seconds / 60, 0)} min</strong><span>estimated travel time</span></div>
      </div>
      <p>ETA {formatTime(route.eta)} · <strong>{route.attribution}</strong></p>
      {route.restrictions_partially_ignored && <p className={styles.inlineWarning}>The provider ignored some vehicle restrictions. This route is incomplete.</p>}
      {route.warnings.length > 0 && <ul>{route.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
      <p className={styles.scope}>Travel time is not construction duration. No route is certified safe or legal.</p>
      <details className={styles.evidenceDetails}><summary>Submitted trip and vehicle</summary><dl className={styles.requestFacts}>
        <div><dt>Origin</dt><dd>{request.origin.lat}, {request.origin.lon}</dd></div><div><dt>Destination</dt><dd>{request.destination.lat}, {request.destination.lon}</dd></div>
        <div><dt>Departure</dt><dd>{formatTime(request.departure_at)}</dd></div><div><dt>Vehicle</dt><dd>{request.truck.height_m}m H · {request.truck.width_m}m W · {request.truck.length_m}m L · {number(request.truck.gross_weight_kg, 0)}kg · {request.truck.axle_count} axles</dd></div>
        <div><dt>Trailers</dt><dd>{request.truck.trailers.length ? request.truck.trailers.map((trailer) => `${trailer.length_m}m`).join(", ") : "Explicitly none"}</dd></div><div><dt>Hazardous goods</dt><dd>{request.truck.hazmat.length ? request.truck.hazmat.join(", ") : "Explicitly none"}</dd></div>
      </dl></details>
    </>}
    {limitations.length > 0 && <details className={styles.evidenceDetails}><summary>Assessment limitations</summary><ul>{limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>}
  </EnvelopeFrame>;
}

export function OutcomePanel({ response }: { response: PredictionResponse }) {
  const prediction = response.prediction;
  return <article className={styles.evidenceCard}>
    <div className={styles.cardHeading}><div><span className="eyebrow">Actual-outcome model</span><h3>Construction duration</h3></div><StatusBadge status={response.status} /></div>
    {!prediction ? <p className={styles.empty}>{response.reason} No numerical estimate is shown.</p> : <>
      <div className={styles.metricRow}>
        <div><strong>{number(prediction.duration_days.median, 0)} days</strong><span>cohort median</span></div>
        <div><strong>{number(prediction.duration_days.lower, 0)}–{number(prediction.duration_days.upper, 0)}</strong><span>evaluated interval, days</span></div>
      </div>
      <p>{prediction.delay_probability == null ? "Duration-overrun probability withheld." : `${number(prediction.delay_probability * 100, 1)}% empirical duration-overrun fraction.`}</p>
      {response.support && <p className={styles.small}>Support: {response.support.training} training · {response.support.calibration} calibration · {response.support.holdout} holdout</p>}
      {response.evaluation && <p className={styles.small}>Evaluated {formatTime(response.evaluation.evaluated_at)} · interval coverage {number(response.evaluation.interval_coverage * 100, 0)}%</p>}
      {response.probability_evidence && <p className={styles.small}>{response.probability_evidence.numerator}/{response.probability_evidence.denominator} training outcomes exceeded the user baseline. {response.probability_evidence.interpretation}</p>}
    </>}
    {response.request && <details className={styles.evidenceDetails}><summary>Submitted cohort and decision context</summary><dl className={styles.requestFacts}><div><dt>Job type</dt><dd>{response.request.job_type}</dd></div><div><dt>Company ID</dt><dd>{response.request.company_id}</dd></div><div><dt>Region</dt><dd>{response.request.region}</dd></div><div><dt>As of</dt><dd>{formatTime(response.request.as_of)}</dd></div><div><dt>Planned baseline</dt><dd>{response.request.planned_duration_days == null ? "Not supplied" : `${response.request.planned_duration_days} days · user confirmed as known then`}</dd></div></dl></details>}
    <details className={styles.evidenceDetails}><summary>Limits</summary><ul>{response.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>
  </article>;
}
