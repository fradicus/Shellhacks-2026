import type { Metadata } from "next";
import Link from "next/link";
import { ImpactWorksheet } from "@/components/impact/ImpactWorksheet";
import { SiteEvidence, type SitePoint } from "@/components/impact/SiteEvidence";
import { SiteFactors } from "@/components/impact/SiteFactors";
import type { MapProject } from "@/components/impact/SiteMap";
import { Badge, ReviewBadge, UtilityBadge, buttonClass, fmtMiles, gapText } from "@/components/ui";
import { getMatches, getPair, getProjects, isFixtureMode } from "@/lib/data";
import { isUnavailable, type Project } from "@/lib/types";
import s from "@/components/impact/impact.module.css";

export const metadata: Metadata = { title: "Impact scenario · Common Ground" };

function projectPoint(project: Project | null | undefined, fallbackLabel: string): SitePoint | null {
  const lat = project?.center?.lat ?? project?.geo?.coordinates?.[1];
  const lon = project?.center?.lon ?? project?.geo?.coordinates?.[0];
  if (lat == null || lon == null || !Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return { label: project?.name ?? fallbackLabel, lat, lon };
}

export default async function ImpactPage({ searchParams }: { searchParams: Promise<{ pair?: string | string[]; tab?: string | string[] }> }) {
  const params = await searchParams;
  const id = typeof params.pair === "string" ? params.pair : "";
  const tab = params.tab === "site" ? "site" : "mobilization";
  const tabHref = (next: string) => `/impact?${new URLSearchParams({ ...(id ? { pair: id } : {}), ...(next === "site" ? { tab: "site" } : {}) })}`;
  const [matches, pair, projectList] = await Promise.all([getMatches({ limit: 100 }), id ? getPair(id) : Promise.resolve(null), tab === "site" ? getProjects() : Promise.resolve([])]);
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
        <span className="eyebrow">Impact scenario / Matting & mobilization</span>
        <h1>Move the package.<br />Understand the tradeoff.</h1>
        <p>A worksheet for project managers weighing a second mobilization against transferring mats or equipment between jobs.</p>
        <Badge>User-entered assumptions · USD</Badge>
        <nav className={`${s.tabs} no-print`} aria-label="Impact worksheets">
          <Link href={tabHref("mobilization")} aria-current={tab === "mobilization" ? "page" : undefined}>Mobilization</Link>
          <Link href={tabHref("site")} aria-current={tab === "site" ? "page" : undefined}>Site factors</Link>
        </nav>
      </header>
      <section className={s.section} aria-labelledby="pair-heading">
        <span className="eyebrow">01 / Project context</span>
        <h2 id="pair-heading">Start with the evidence.</h2>
        <form action="/impact" className={`${s.picker} no-print`}>
          {tab === "site" && <input type="hidden" name="tab" value="site" />}
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
          {!sitePoints.length && <p className={s.muted}>Neither project center has published coordinates, so Field planning context is not attached.</p>}
        </> : !id && <p className={s.muted}>No pair attached. Use this worksheet for your own two-job scenario, or choose a pair to keep its source evidence alongside your assumptions.</p>}
      </section>
      {tab === "site" ? <SiteFactors key={`factors-${id}`} pairLabel={pairLabel} points={sitePoints} projects={mapProjects} /> : <>
        {sitePoints.length > 0 && <SiteEvidence key={`site-${id}`} points={sitePoints} />}
        <ImpactWorksheet key={id} pairLabel={pairLabel} />
      </>}
      <aside className={s.research}>
        <strong>Why these inputs?</strong> Sponsor conversations highlighted freight, short-notice mobilization and idle rented equipment.
        One contractor described $1.5M in freight on a $5M job. That anecdote is context only; it is not a default rate or savings ratio.
        Dakota describes access planning, mat installation/removal and rentals in its <a href="https://dakotamats.com/about/" target="_blank" rel="noreferrer">service overview</a>.
      </aside>
    </main>
  );
}
