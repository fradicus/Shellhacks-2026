import Link from "next/link";
import { HeroStory } from "./HeroStory";
import { HeroScene } from "./HeroScene";
import { Integrations } from "./Integrations";
import { NetworkIllustration } from "./NetworkIllustration";
import s from "./landing.module.css";

export function Arrow({ diagonal = false }: { diagonal?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h15m-6-6 6 6-6 6"}
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LandingPage() {
  return (
    <div className={s.landing}>
      <main className={s.main} id="main-content">
        <HeroStory>
          <section className={s.hero} aria-labelledby="hero-title">
            <h1 id="hero-title" className={s.srOnly}>
              Common Ground — Find nearby utility projects.
            </h1>
            <HeroScene />
            <a href="#the-corridor" className={s.scrollHint}>
              DISCOVER THE NETWORK <span aria-hidden="true">↓</span>
            </a>
          </section>
        </HeroStory>

        <section className={s.corridor} id="the-corridor" aria-labelledby="corridor-title">
          <div className={s.corridorMap}>
            <NetworkIllustration />
            <span className={s.mapCaption}>
              <i /> ILLUSTRATIVE U.S. NETWORK · NOT LIVE FLEET DATA
            </span>
          </div>
          <div className={s.corridorCopy}>
            <p className={s.eyebrow}>01 / A SHARED CORRIDOR</p>
            <h2 id="corridor-title">
              Closer than
              <br />
              they look.
            </h2>
            <p>
              Explore public project records by state. Coverage varies by source; the national view helps you see what is available and where evidence is missing.
            </p>
            <div className={s.metrics}>
              <div>
                <strong>
                  &lt;25<span>mi</span>
                </strong>
                <p>Project-center distance</p>
              </div>
              <div>
                <strong>50</strong>
                <p>States in the national view</p>
              </div>
            </div>
            <div className={s.scopeNote}>
              <span aria-hidden="true">↗</span>
              <p>Nearby projects are leads to investigate. In-service dates are milestones, not construction schedules or proof that crews can work together.</p>
            </div>
            <Link href="/time" className={s.textLink}>
              Compare nearby projects <Arrow />
            </Link>
          </div>
        </section>

        <section className={s.section} id="workspace" aria-labelledby="workspace-title">
          <div className={s.sectionHeading}>
            <div>
              <p className={s.eyebrow}>02 / A CONNECTED WORKSPACE</p>
              <h2 id="workspace-title">From the project.<br /><span>To the worksite.</span></h2>
            </div>
            <p>Find the project, understand the site, and bring the evidence into your next planning conversation.</p>
          </div>
          <div className={s.workspaceGrid}>
            <div className={s.workspaceTools}>
              {[
                { href: "/explore", title: "Find nearby work", text: "Browse projects by state and county, with the public records behind each location." },
                { href: "/changes", title: "Follow the changes", text: "Compare filing versions and see what changed in the published plan." },
                { href: "/operations", title: "Understand the site", text: "Review available weather, water, soil, and annual satellite evidence." },
                { href: "/impact", title: "Build a cost scenario", text: "Bring your own crew, contractor, and equipment rates into the calculation." },
              ].map((tool) => (
                <Link key={tool.href} href={tool.href} className={s.workspaceTool}>
                  <div><h3>{tool.title}</h3><p>{tool.text}</p></div>
                  <Arrow diagonal />
                </Link>
              ))}
            </div>
            <div className={s.workspaceVisual} id="connected">
              <Integrations />
              <p>Public evidence and your inputs, brought together. Availability varies by location; work-zone data covers Washington and satellite evidence is annual.</p>
            </div>
          </div>
        </section>

        <section className={`${s.section} ${s.method}`} id="how-it-works" aria-labelledby="method-title">
          <div className={s.sectionHeading}>
            <div>
              <p className={s.eyebrow}>03 / HOW IT WORKS</p>
              <h2 id="method-title">A connection you can see.<br /><span>Evidence you can check.</span></h2>
            </div>
            <p>We turn separate public records into a shared view of nearby work, while keeping the original evidence within reach.</p>
          </div>
          <ol className={s.methodFlow} aria-label="From public records to planning evidence">
            <li><span>01</span>Public records</li>
            <li><span>02</span>Structured project data</li>
            <li><span>03</span>Nearby project comparisons</li>
            <li><span>04</span>Evidence for your plan</li>
          </ol>
          <div className={s.methodGrid}>
            <div className={s.methodPlain}>
              <p className={s.methodLabel}>IN PLAIN LANGUAGE</p>
              <h3>Less document hunting.<br />A better starting point.</h3>
              <p>Two utilities can publish plans for work a few miles apart without seeing each other’s projects. Common Ground brings those records onto one map so a project manager can investigate the connection.</p>
              <p>Open a project to see where the information came from, compare nearby work, and review available site conditions. Add your own rates to explore costs, then take the supporting evidence into a planning conversation.</p>
              <div className={s.methodNote}>A nearby project is a lead to investigate. A filed in-service date does not tell you when construction crews will be on site.</div>
              <Link href="/coverage" className={s.textLink}>Check the source coverage <Arrow /></Link>
            </div>
            <div className={s.methodTechnical}>
              <p className={s.methodLabel}>UNDER THE HOOD</p>
              <p className={s.methodHint}>Open a topic for the technical detail.</p>
              <details className={s.methodDetail}>
                <summary>From filings to structured records<span aria-hidden="true">+</span></summary>
                <div>
                  <p>Python extraction pipelines turn public filings into project records. JSON Schema validation checks the record structure; source references, original date text, and location evidence remain attached to the data.</p>
                  <p>Schema validation checks format and required fields. Location confidence and source evidence still need review.</p>
                </div>
              </details>
              <details className={s.methodDetail}>
                <summary>How nearby projects are compared<span aria-hidden="true">+</span></summary>
                <div>
                  <p>The legacy DESC–Georgia Power matching engine uses haversine distance between project centers. Different utilities, known centers, and a distance strictly below 25 miles qualify as an overlap.</p>
                  <p>Centers use the mean latitude and longitude of located endpoints, or the one available endpoint. Exact day gaps are calculated only when both filed dates have day precision. National nearby candidates are labeled provisional and carry their own location evidence.</p>
                </div>
              </details>
              <details className={s.methodDetail}>
                <summary>How the app serves the evidence<span aria-hidden="true">+</span></summary>
                <div>
                  <p>Versioned datasets are loaded into MongoDB. The Next.js and TypeScript app reads through server APIs; Three.js provides the planning view, and MapLibre provides geographic maps.</p>
                  <p>The database loader activates a dataset after validation. Missing database access produces an unavailable state rather than silently substituting sample data.</p>
                </div>
              </details>
              <details className={s.methodDetail}>
                <summary>How site context and costs stay grounded<span aria-hidden="true">+</span></summary>
                <div>
                  <p>Environmental providers return evidence with availability, timestamps, and coverage limits. AlphaEarth Foundations supplies annual satellite embeddings for available point-and-year samples; it is not a live satellite feed.</p>
                  <p>Cost scenarios use the inputs you supply. Missing rates stay unknown, and a scenario is not a quote or a promise of savings.</p>
                </div>
              </details>
            </div>
          </div>
        </section>

        <section className={s.finalCta}>
          <p className={s.eyebrow}>THE GRID IS CONNECTED. YOUR PLANS CAN BE, TOO.</p>
          <h2>
            See what’s
            <br />
            <span>just down the road.</span>
          </h2>
          <Link href="/time" className={s.primary}>
            Explore nearby projects <Arrow />
          </Link>
          <p>Discover a lead. Check the evidence. Start a conversation.</p>
        </section>

      </main>
      <footer className={s.closing}>
        <div className={s.closingTop}>
          <div>
            <Link href="/" className={s.footerBrand}>Common Ground<span>Every mile. Connected.</span></Link>
            <p className={s.closingDescription}>A clearer view of nearby utility work, grounded in public records.</p>
          </div>
          <nav aria-label="Footer" className={s.closingLinks}>
            <Link href="/time">Explore overlaps <Arrow diagonal /></Link>
            <Link href="/explore">Browse projects <Arrow diagonal /></Link>
            <Link href="/coverage">Sources & coverage <Arrow diagonal /></Link>
          </nav>
        </div>
        <div className={s.closingBottom}>
          <p>Built on public utility filings, including Dominion Energy South Carolina and Georgia Power.</p>
          <span>Network illustrations are conceptual.</span>
        </div>
      </footer>
    </div>
  );
}
