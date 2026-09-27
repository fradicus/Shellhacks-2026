import type { LocationVerification } from "../../lib/national/types";

export function LocationEvidence({ verification }: { verification: LocationVerification }) {
  const latest = verification.reviews.at(-1);
  const meaning = verification.location_kind === "site"
    ? "Substation site point"
    : verification.points.length === 2
      ? "Complete endpoint coverage: map point is the mean of two endpoints"
      : "Partial endpoint coverage: map point is the one known endpoint";
  return (
    <section aria-label="Reviewed location evidence">
      <h3>Location evidence</h3>
      <p><strong>{meaning}</strong></p>
      <p>Location confirmation is separate from construction status.</p>
      {verification.points.map((point) => (
        <details key={point.role}>
          <summary>{point.facility_name} · {point.role === "site" ? "site" : `endpoint ${point.role.toUpperCase()}`}</summary>
          <p>Facility: {point.facility_id} · WGS84: {point.lat}, {point.lon}</p>
          <p>Precision: {point.precision ?? "Not reported"} · Positional uncertainty: {point.uncertainty_m === null ? "Not reported" : `${point.uncertainty_m} m`}</p>
          <p>{point.identity_rationale}</p>
          <p>Original geometry: {point.original_geometry.crs} · {point.original_geometry.coordinates.join(", ")}</p>
          <p>Conversion: {point.original_geometry.transform}</p>
          {(["geometry_evidence", "identity_evidence"] as const).map((kind) => (
            <div key={kind}>
              <h4>{kind === "geometry_evidence" ? "Location sources" : "Project identity sources"}</h4>
              <ul>{point[kind].map((source, index) => (
                <li key={`${source.artifact_sha256}-${index}`}>
                  <a href={source.url} target="_blank" rel="noreferrer">{source.publisher} · {source.locator}</a>
                  <p>Source date: {source.source_date ?? "Not reported"} · Retrieved: {source.retrieved_at}</p>
                  <p>{source.facts}</p>
                  <p>Access: {source.access_review}</p>
                  <p>SHA-256: <code>{source.artifact_sha256}</code></p>
                </li>
              ))}</ul>
            </div>
          ))}
        </details>
      ))}
      {latest ? <details>
        <summary>Latest independent review: {latest.decision} · {latest.reviewer}</summary>
        <p>Reviewed: {latest.reviewed_at}</p>
        <p>{latest.reason}</p>
        <p>Reviewed facts SHA-256: <code>{latest.facts_sha256}</code></p>
      </details> : <p>Independent review: Not reported</p>}
    </section>
  );
}
