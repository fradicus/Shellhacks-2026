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
            <div className={s.heroIntro}>
              <p>TRANSMISSION PROJECT PLANNING</p>
              <span>Find nearby utility projects. Compare the evidence.</span>
              <Link href="/time">Explore nearby projects <Arrow /></Link>
            </div>
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
