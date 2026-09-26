import type { Metadata } from "next";
import Link from "next/link";
import { ImpactWorksheet } from "@/components/impact/ImpactWorksheet";
import { Badge, ReviewBadge, UtilityBadge, buttonClass, fmtMiles, gapText } from "@/components/ui";
import { getMatches, getPair, isFixtureMode } from "@/lib/data";
import { isUnavailable } from "@/lib/types";
import s from "@/components/impact/impact.module.css";

export const metadata: Metadata = { title: "Impact scenario · GridBridge" };

export default async function ImpactPage({ searchParams }: { searchParams: Promise<{ pair?: string | string[] }> }) {
  const params = await searchParams;
  const id = typeof params.pair === "string" ? params.pair : "";
  const [matches, pair] = await Promise.all([getMatches({ limit: 100 }), id ? getPair(id) : Promise.resolve(null)]);
  const detail = pair && !isUnavailable(pair) ? pair : null;
  const rows = isUnavailable(matches) ? [] : matches;
  const match = detail?.match;
  return (
    <main className={s.page}>
      <header className={s.hero}>
        <span className="eyebrow">Impact scenario / Matting & mobilization</span>
        <h1>Move the package.<br />Understand the tradeoff.</h1>
        <p>A worksheet for project managers weighing a second mobilization against transferring mats or equipment between jobs.</p>
        <Badge>User-entered assumptions · USD</Badge>
      </header>
      <section className={s.section} aria-labelledby="pair-heading">
        <span className="eyebrow">01 / Project context</span>
        <h2 id="pair-heading">Start with the evidence.</h2>
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
        </> : !id && <p className={s.muted}>No pair attached. Use this worksheet for your own two-job scenario, or choose a pair to keep its source evidence alongside your assumptions.</p>}
      </section>
      <ImpactWorksheet key={id} pairLabel={detail ? `${detail.a?.name ?? match?.a} / ${detail.b?.name ?? match?.b}` : null} />
      <aside className={s.research}>
        <strong>Why these inputs?</strong> Sponsor conversations highlighted freight, short-notice mobilization and idle rented equipment.
        One contractor described $1.5M in freight on a $5M job. That anecdote is context only; it is not a default rate or savings ratio.
        Dakota describes access planning, mat installation/removal and rentals in its <a href="https://dakotamats.com/about/" target="_blank" rel="noreferrer">service overview</a>.
      </aside>
    </main>
  );
}
