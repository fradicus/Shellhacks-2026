import type { Metadata } from "next";
import Link from "next/link";
import type { SitePoint } from "@/components/impact/SiteEvidence";
import { SiteFactors } from "@/components/impact/SiteFactors";
import type { MapProject } from "@/components/impact/SiteMap";
import { Badge, ReviewBadge, UtilityBadge, buttonClass, fmtMiles, gapText } from "@/components/ui";
import { getMatches, getPair, getProjects, isFixtureMode } from "@/lib/data";
import { isUnavailable, type Project } from "@/lib/types";
import s from "@/components/impact/impact.module.css";

export const metadata: Metadata = { title: "Site weather report · Common Ground" };

function projectPoint(project: Project | null | undefined, fallbackLabel: string): SitePoint | null {
  const lat = project?.center?.lat ?? project?.geo?.coordinates?.[1];
  const lon = project?.center?.lon ?? project?.geo?.coordinates?.[0];
  if (lat == null || lon == null || !Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return { label: project?.name ?? fallbackLabel, lat, lon };
}

export default async function ImpactPage({ searchParams }: { searchParams: Promise<{ pair?: string | string[] }> }) {
  const params = await searchParams;
  const id = typeof params.pair === "string" ? params.pair : "";
  const [matches, pair, projectList] = await Promise.all([getMatches({ limit: 100 }), id ? getPair(id) : Promise.resolve(null), getProjects()]);
  const detail = pair && !isUnavailable(pair) ? pair : null;
  const rows = isUnavailable(matches) ? [] : matches;
  const match = detail?.match;
  const sitePoints = detail && match
    ? [projectPoint(detail.a, match.a ?? "Project A"), projectPoint(detail.b, match.b ?? "Project B")].filter((point): point is SitePoint => point !== null)
    : [];
  const pairLabel = detail ? `${detail.a?.name ?? match?.a} / ${detail.b?.name ?? match?.b}` : null;
  // Same located-point rule as the pair points above; unlocated projects stay off the map.
  const pairKeys = new Set([detail?.a?.project_key, detail?.b?.project_key].filter(Boolean));
  const mapProjects: MapProject[] = isUnavailable(projectList) ? [] : projectList.flatMap((project) => {
    const point = projectPoint(project, project.project_key);
    return point ? [{ key: project.project_key, name: project.name, utility: project.utility, lat: point.lat, lon: point.lon, confidence: project.location_confidence ?? null, inPair: pairKeys.has(project.project_key) }] : [];
  });
  return (
    <main className={s.page}>
      <header className={s.hero}>
        <span className="eyebrow">Impact / Site weather report</span>
        <h1>Pick a site.<br />Price the weather delay.</h1>
        <p>Replay ten years of NOAA station weather for a U.S. location, then add last year, the NWS forecast, and flood, wetland, and soil context. The dollar figures use the rates you enter.</p>
        <Badge>Historical replay · your rates</Badge>
      </header>

      <section className={s.section} aria-labelledby="pair-heading">
        <span className="eyebrow">Optional · project pair</span>
        <h2 id="pair-heading">Attach a project pair.</h2>
        <p className={s.muted}>Adds both project centers as one-click sites and keeps their filing evidence with this worksheet.</p>
        <form action="/impact" className={`${s.picker} no-print`}>
          <label htmlFor="pair">Project pair (optional)
            <select id="pair" name="pair" defaultValue={id}>
              <option value="">Standalone worksheet</option>
              {id && !rows.some((row) => row._id === id) && <option value={id}>{detail ? `${detail.a?.name ?? match?.a} / ${detail.b?.name ?? match?.b}` : "Requested pair unavailable"}</option>}
              {rows.map((row) => <option key={row._id} value={row._id}>{row.project_a?.name ?? row.a} / {row.project_b?.name ?? row.b} · {row.review_state ?? "needs_review"}</option>)}
            </select>
          </label>
          <button className={buttonClass} type="submit">Open worksheet</button>
        </form>
        <p className={s.muted}>Changing the pair opens a fresh worksheet. Up to 100 pairs from the active dataset are listed.</p>
        {isFixtureMode() && <p className={s.warning}>Sponsor sample / fixture data. Project context here is for demonstration.</p>}
        {isUnavailable(matches) && <p className={s.warning}>Project list unavailable. You can still enter a standalone scenario; no sample projects have been substituted.</p>}
        {id && !detail && <p className={s.warning}>{pair && isUnavailable(pair) ? "The requested pair could not be loaded." : "The requested pair was not found in the active dataset."} No project facts are attached to this worksheet.</p>}
        {detail && match ? <>
          <div className={s.facts}><strong>{fmtMiles(match.distance_mi)}</strong><span>{gapText(match.time_gap_days)}</span><ReviewBadge state={match.review_state} /><Badge>{match.view}</Badge></div>
          <div className={s.pair}>{([detail.a, detail.b] as const).map((project, index) => {
            const source = detail.sources?.find((item) => item._id === project?.source.source_id);
            const safeUrl = source?.url && /^https?:\/\//i.test(source.url) ? source.url : null;
            return <article className={s.project} key={index}>
              <span className="eyebrow">Project {index === 0 ? "A" : "B"}</span>
              <h3>{project?.name ?? (index === 0 ? match.a : match.b)}</h3>
              <UtilityBadge utility={project?.utility ?? "unknown"} />
              <p>Filed in-service: {project?.in_service.raw ?? "Unknown"} · precision: {project?.in_service.precision ?? "unknown"}</p>
              <p>{project ? <>Source: {source?.title ?? project.source.source_id} · page {project.source.page ?? "unknown"}</> : "Project record unavailable."}</p>
              {safeUrl && <a href={`${safeUrl.split("#")[0]}${project?.source.page ? `#page=${project.source.page}` : ""}`} target="_blank" rel="noreferrer">Open source document ↗</a>}
            </article>;
          })}</div>
          <p className={s.warning}>{match.review_state === "rejected" ? "This pair was rejected in review. Its costs can be explored hypothetically, but it is not a validated coordination opportunity. " : match.review_state !== "confirmed" ? "This pair still needs review. " : "Review does not establish equipment availability. "}Center distance is not a truck route. Filed in-service dates are not construction windows.</p>
          <Link href={`/pair/${encodeURIComponent(match._id)}`}>Inspect pair evidence and review details →</Link>
          {!sitePoints.length && <p className={s.muted}>Neither project center has published coordinates, so pick the site on the map below.</p>}
        </> : !id && <p className={s.muted}>No pair attached. Choose one to keep its filing evidence with your rates, or continue with a standalone site.</p>}
      </section>
      <SiteFactors key={`factors-${id}`} pairLabel={pairLabel} points={sitePoints} projects={mapProjects} />
      <aside className={s.research}>
        <strong>Where the numbers come from.</strong> Daily rain, temperature, snow and wind: <a href="https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily" target="_blank" rel="noreferrer">NOAA NCEI GHCN-Daily</a> station records, 2016–2025, plus the latest observations.
        Forecast: National Weather Service. Flood zones: FEMA NFHL. Wetlands: USFWS NWI. Soil: USDA SSURGO. Wetland permit times: <a href="https://www.govinfo.gov/content/pkg/FR-2025-06-18/html/2025-11190.htm" target="_blank" rel="noreferrer">USACE FY2024 averages</a>.
        Costs are always your own rates; nothing here is a bid or a forecast guarantee.
      </aside>
    </main>
  );
}
