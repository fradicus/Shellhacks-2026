import type { NationalProject } from "../../lib/national/types";
import { displayPoints, locationLabel } from "../../lib/national/locations";

export function LocationSummary({ project }: { project: NationalProject }) {
  const area = project.approximate_location;
  const candidate = project.location_candidate;
  return <section aria-label="Location precision">
    <p><strong>{locationLabel(project)}</strong></p>
    {project.center ? <p>{project.center.basis === "two" ? "Mean of two located endpoints."
      : project.center.basis === "one" ? "Partial location: one known endpoint." : "Source reference point."}</p> : null}
    {candidate || (project.center && project.location_review !== "confirmed") ? <>
      <p>{candidate?.note ?? project.center?.evidence ?? "Not independently reviewed."}</p>
      {candidate?.attribution ? <p><a href={candidate.license_url ?? "https://www.openstreetmap.org/copyright"}
        target="_blank" rel="noreferrer">{candidate.attribution}</a></p> : null}
      {candidate?.endpoints?.length ? <details><summary>Facility references</summary><ul>
        {candidate.endpoints.map((point) => <li key={`${point.side}-${point.osm_id}`}>
          {point.side}: {point.url ? <a href={point.url} target="_blank" rel="noreferrer">{point.names?.name ?? point.osm_id}</a> : point.names?.name}
        </li>)}
      </ul></details> : null}
    </> : null}
    {!project.center && area && displayPoints(project).length ? <>
      <p>{area.anchors.map((a) => a.county_name).join(" · ")}. The marker represents the county, not the project site.</p>
      <details><summary>County reference source</summary>
        <a href={area.reference_source.url} target="_blank" rel="noreferrer">Census reference geography</a>
        <p>Retrieved: {area.reference_source.retrieved_at}</p>
        <p>Method: {Array.from(new Set(area.anchors.map((a) => a.method))).join("; ")}</p>
        <p>SHA-256: <code>{area.reference_source.sha256}</code></p>
      </details>
    </> : null}
  </section>;
}
