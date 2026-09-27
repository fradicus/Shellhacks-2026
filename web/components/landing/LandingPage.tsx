import Link from "next/link";
import { HeroStory } from "./HeroStory";
import { HeroScene } from "./HeroScene";
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
              Common Ground — Every mile. Connected.
            </h1>
            <HeroScene />
            <a href="#how-it-works" className={s.scrollHint}>
              FOLLOW THE CONNECTION <span aria-hidden="true">↓</span>
            </a>
          </section>
        </HeroStory>

        <section className={`${s.section} ${s.workflow}`} id="how-it-works" aria-labelledby="how-title">
          <div className={s.sectionHeading}>
            <div>
              <p className={s.eyebrow}>01 / CONNECT THE DOTS</p>
              <h2 id="how-title">
                Separate filings.
                <br />
                <span>A bigger picture.</span>
              </h2>
            </div>
            <div className={s.headingSide}>
              <p>
                Neighboring utilities plan work independently. Common Ground brings the records together, so you can spot
                nearby projects and investigate the evidence behind them.
              </p>
              <div className={s.actions}>
                <Link href="/time" className={s.primary}>
                  Explore the overlaps <Arrow />
                </Link>
                <Link href="/explore" className={s.secondary}>
                  Browse by state <span aria-hidden="true">↗</span>
                </Link>
              </div>
            </div>
          </div>
          <div className={s.steps}>
            <article className={s.step}>
              <div className={s.stepTop}>
                <span>01</span>
                <svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
                  <path d="M14 7h16l8 8v26H14zM30 7v9h8M20 23h12M20 29h12M20 35h7" stroke="currentColor" strokeWidth="1.4" />
                  <path d="M9 13H7v29h23" stroke="currentColor" strokeOpacity=".35" />
                </svg>
              </div>
              <h3>Start with the source.</h3>
              <p>Public filings become project records with the utility, dates, location evidence, and source page kept in view.</p>
            </article>
            <article className={s.step}>
              <div className={s.stepTop}>
                <span>02</span>
                <svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
                  <circle cx="18" cy="24" r="13" stroke="currentColor" strokeWidth="1.4" />
                  <circle cx="31" cy="24" r="13" stroke="currentColor" strokeWidth="1.4" />
                  <path d="M18 24h13" stroke="currentColor" strokeDasharray="2 3" />
                  <circle cx="18" cy="24" r="2" fill="currentColor" />
                  <circle cx="31" cy="24" r="2" fill="currentColor" />
                </svg>
              </div>
              <h3>Find the common ground.</h3>
              <p>Discover cross-utility project centers less than 25 miles apart. Compare their timing and review location confidence.</p>
            </article>
            <article className={s.step}>
              <div className={s.stepTop}>
                <span>03</span>
                <svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
                  <path d="M9 9h30v23H22l-9 8v-8H9zM16 17h16M16 24h10" stroke="currentColor" strokeWidth="1.4" />
                </svg>
              </div>
              <h3>Make the next conversation count.</h3>
              <p>Open the pair evidence, check what is still uncertain, and export a coordination card for the people planning the work.</p>
            </article>
          </div>
        </section>

        <section className={s.corridor} id="the-corridor" aria-labelledby="corridor-title">
          <div className={s.corridorMap}>
            <NetworkIllustration />
            <span className={s.mapCaption}>
              <i /> ILLUSTRATIVE U.S. NETWORK · NOT LIVE FLEET DATA
            </span>
          </div>
          <div className={s.corridorCopy}>
            <p className={s.eyebrow}>02 / A SHARED CORRIDOR</p>
            <h2 id="corridor-title">
              Closer than
              <br />
              they look.
            </h2>
            <p>
              Across the country, nearby work can sit in separate plans. Start with the evidence. Follow what connects.
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
              <p>Distance identifies a lead. Source evidence, timing, and a planner’s review determine what comes next.</p>
            </div>
            <Link href="/time" className={s.textLink}>
              Investigate the corridor <Arrow />
            </Link>
          </div>
        </section>

        <section className={s.section} id="workspace" aria-labelledby="workspace-title">
          <div className={s.sectionHeading}>
            <div>
              <p className={s.eyebrow}>03 / YOUR NEXT MOVE</p>
              <h2 id="workspace-title">
                Less searching.
                <br />
                <span>More understanding.</span>
              </h2>
            </div>
            <p>Move from the big picture to the supporting record. Your research tools are already connected.</p>
          </div>
          <div className={s.tools}>
            <Link href="/explore" className={`${s.tool} ${s.toolLarge}`}>
              <div className={s.toolVisual} aria-hidden="true">
                <div className={s.crosshair} />
                <span className={s.coord}>STATE → COUNTY → SOURCE</span>
                <div className={s.orbit} />
                <div className={s.orbitSmall} />
                <span className={s.mapPoint} />
              </div>
              <div className={s.toolBody}>
                <span className={s.toolLabel}>
                  THE WIDER VIEW <Arrow diagonal />
                </span>
                <h3>Find your place in the network.</h3>
                <p>Browse the national explorer by geography and inspect the source coverage available for each area.</p>
                <span className={s.toolAction}>
                  Open national explorer <Arrow />
                </span>
              </div>
            </Link>
            <div className={s.toolStack}>
              <Link href="/changes" className={s.tool}>
                <div className={s.toolBody}>
                  <span className={s.toolLabel}>
                    FILING CHANGES <Arrow diagonal />
                  </span>
                  <h3>
                    Plans change.
                    <br />
                    Keep the context.
                  </h3>
                  <p>Compare filing versions and see what changed in the published record.</p>
                  <span className={s.toolAction}>
                    Review changes <Arrow />
                  </span>
                </div>
                <div className={s.changeArt} aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
              </Link>
              <Link href="/coverage" className={s.tool}>
                <div className={s.toolBody}>
                  <span className={s.toolLabel}>
                    EVIDENCE & COVERAGE <Arrow diagonal />
                  </span>
                  <h3>Know what you know.</h3>
                  <p>Check source coverage and uncertainty before you act on a lead.</p>
                  <span className={s.toolAction}>
                    See coverage <Arrow />
                  </span>
                </div>
              </Link>
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
            Find the connection <Arrow />
          </Link>
          <p>Discover a lead. Check the evidence. Start a conversation.</p>
        </section>

        <div className={s.proofStrip}>
          <span>
            GROUNDED IN
            <br />
            <b>PUBLIC UTILITY FILINGS</b>
          </span>
          <div>
            Dominion Energy <span>South Carolina</span>
          </div>
          <span className={s.plus} aria-hidden="true">
            +
          </span>
          <div>
            Georgia Power <span>Georgia</span>
          </div>
          <Link href="/coverage">
            See the evidence <Arrow diagonal />
          </Link>
        </div>
      </main>
      <footer className={s.footer}>
        <Link href="/" className={s.footerBrand}>
          Common Ground<span>Every mile. Connected.</span>
        </Link>
        <div>
          <Link href="/time">Overlaps</Link>
          <Link href="/explore">National explorer</Link>
          <Link href="/coverage">Source coverage</Link>
        </div>
        <p>
          Coordination discovery from public records.
          <br />
          Illustrations are conceptual. Project evidence stays in the app.
        </p>
      </footer>
    </div>
  );
}
