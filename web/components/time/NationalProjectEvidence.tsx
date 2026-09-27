import { LocationEvidence } from "@/components/national/LocationEvidence";
import { STATUS_LABEL } from "@/lib/national/filters";
import { locationLabel } from "./nationalProjects";
import type { NationalProject, NationalSource } from "@/lib/national/types";
import s from "./time.module.css";

export function NationalProjectEvidence({ project, source, dataset }: { project: NationalProject; source?: NationalSource; dataset: string | null }) {
  const locator = [project.evidence.page !== null ? `page ${project.evidence.page}` : null,
    project.evidence.sheet, project.evidence.row !== null ? `row ${project.evidence.row}` : null].filter(Boolean).join(" · ");
  const basis = project.center?.basis === "two" ? "Mean of two located endpoints"
    : project.center?.basis === "one" ? "Partial location: one known endpoint" : "Source site point";
  return <div className={s.nationalEvidence}>
    <p><code>{project._id}</code> · source ID {project.native_id}</p>
    <p>Filed status: {project.status ?? STATUS_LABEL[project.status_group]}. This is the source observation, not a live construction update.</p>
    {project.other_owners.length ? <p>Other filed owners: {project.other_owners.join(", ")}</p> : null}
    <p>{locationLabel(project)} · {basis}</p>
    <p>Filed milestone: {project.in_service.raw ?? "Unknown"} ({project.in_service.precision})</p>
    <p>{source?.publisher ?? project.source_id} · {locator || "Source locator not reported"}</p>
    <p>Published: {source?.publication_date ?? "Unknown"} · Vintage: {source?.vintage ?? "Unknown"} · Retrieved: {source?.retrieved_at ?? "Unknown"}</p>
    {source?.landing_url ? <p><a href={source.landing_url} target="_blank" rel="noreferrer">Open project source ↗</a></p> : null}
    {project.location_verification ? <LocationEvidence verification={project.location_verification} />
      : <p>{project.center?.evidence ?? "Detailed location evidence not reported."}</p>}
    <p>Dataset: <code>{dataset ?? "Unknown"}</code></p>
    <p>National discovery point; overlap matching has not been run for this project.</p>
  </div>;
}
