import Link from "next/link";
import { HeroScene } from "./HeroScene";
import { NetworkIllustration } from "./NetworkIllustration";
import s from "./landing.module.css";

export function Arrow({diagonal=false}:{diagonal?:boolean}) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h15m-6-6 6 6-6 6"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

export function LandingPage({fixtureMode}:{fixtureMode:boolean}) {
  return <div className={s.landing}>
    <main className={s.main} id="main-content">
      <section className={s.hero} aria-labelledby="hero-title">
        <div className={s.heroContent}>
          {/* Hero strings from docs/GridBridge-reference.html final overlay + scroll-story beats. */}
          <h1 id="hero-title">GridBridge</h1>
          <p className={s.heroTag}>Every mile. Connected.</p>
          <div className={s.actions}>
            <a href="#how-it-works" className={s.primary}>See how it works <Arrow/></a>
          </div>
          <p className={s.heroNote}>{fixtureMode ? "Sample data available · No account needed" : "Public-source evidence · No account needed"}</p>
        </div>
        <p className={s.sr}>GridBridge. Every mile. Connected. A truck drives through the title, then the view tilts down to a network of trucks across the Southeast United States.</p>
        <HeroScene/>
        <a href="#how-it-works" className={s.scrollHint}>Scroll <span aria-hidden="true">↓</span></a>
      </section>

      <div className={s.proofStrip}>
        <span>GROUNDED IN<br/><b>PUBLIC UTILITY FILINGS</b></span>
        <div>Dominion Energy <span>South Carolina</span></div>
        <span className={s.plus} aria-hidden="true">+</span>
        <div>Georgia Power <span>Georgia</span></div>
        <Link href="/coverage">See the evidence <Arrow diagonal/></Link>
      </div>

      <section className={`${s.section} ${s.workflow}`} id="how-it-works" aria-labelledby="how-title">
        <div className={s.sectionHeading}>
          <div><p className={s.eyebrow}>How it works</p><h2 id="how-title">From filing to fleet move.</h2></div>
          <p>Utilities publish their construction plans in long public filings. Two companies can schedule work a few miles apart and never know it. <b>GridBridge reads both and puts the overlaps on one map.</b></p>
        </div>
        <div className={s.steps}>
          <article className={s.step}><div className={s.stepTop}><span>Step 1</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M14 7h16l8 8v26H14zM30 7v9h8M20 23h12M20 29h12M20 35h7" stroke="currentColor" strokeWidth="1.4"/><path d="M9 13H7v29h23" stroke="currentColor" strokeOpacity=".35"/></svg></div><h3>Read the filings.</h3><p>Projects from <b>Dominion Energy South Carolina</b> and <b>Georgia Power</b> filings are placed on the map and checked against the page they came from.</p><span className={s.stepOut}>Project · utility · location · source page</span><Link href="/coverage">Inspect coverage <Arrow/></Link></article>
          <article className={s.step}><div className={s.stepTop}><span>Step 2</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><circle cx="18" cy="24" r="13" stroke="currentColor" strokeWidth="1.4"/><circle cx="31" cy="24" r="13" stroke="currentColor" strokeWidth="1.4"/><path d="M18 24h13" stroke="currentColor" strokeDasharray="2 3"/><circle cx="18" cy="24" r="2" fill="currentColor"/><circle cx="31" cy="24" r="2" fill="currentColor"/></svg></div><h3>Find the overlaps.</h3><p>Every cross-utility pair is measured by straight-line distance. <b>Pairs under 25 miles</b> are ranked and shown with the evidence behind them.</p><span className={s.stepOut}>Pair · distance in miles · evidence</span><Link href="/time">Explore overlaps <Arrow/></Link></article>
          <article className={s.step}><div className={s.stepTop}><span>Step 3</span><svg viewBox="0 0 48 48" fill="none" aria-hidden="true"><path d="M9 9h30v23H22l-9 8v-8H9zM16 17h16M16 24h10" stroke="currentColor" strokeWidth="1.4"/></svg></div><h3>Move once.</h3><p><b>MatFlow</b> takes a confirmed pair and plans the transfer: which trucks carry which mats from one job to the next, solved with OR-Tools.</p><span className={s.stepOut}>Transfer plan · trucks · mats · cost</span><Link href="/map">Open the project map <Arrow/></Link></article>
        </div>
      </section>

      <section className={s.corridor} id="the-corridor" aria-labelledby="corridor-title">
        <div className={s.corridorMap}><NetworkIllustration/><span className={s.mapCaption}><i/> ILLUSTRATIVE NETWORK · NOT LIVE FLEET DATA</span></div>
        <div className={s.corridorCopy}>
          <p className={s.eyebrow}>The corridor</p>
          <h2 id="corridor-title">Built for the Southeast.</h2>
          <p>The first dataset covers South Carolina and Georgia, where the two service areas meet along the Savannah River. The network view carries the same idea across the interstates that already move the freight.</p>
          <div className={s.metrics}><div><strong>25<span>mi</span></strong><p>Overlap radius</p></div><div><strong>2</strong><p>Utilities in the first dataset</p></div><div><strong>7</strong><p>States in the network view</p></div></div>
          <div className={s.chips}><span>I-95</span><span>I-75</span><span>I-85</span><span>I-20</span><span>I-26</span><span>I-16</span><span>I-10</span><span>I-40</span><span>I-65</span></div>
          <p className={s.states}>FL · GA · SC · NC · AL · TN · MS</p>
          <Link href="/time" className={s.textLink}>Investigate the corridor <Arrow/></Link>
        </div>
      </section>

      <section className={s.section} id="workspace" aria-labelledby="workspace-title">
        <div className={s.sectionHeading}><div><p className={s.eyebrow}>03 / YOUR NEXT MOVE</p><h2 id="workspace-title">Less searching.<br/><span>More understanding.</span></h2></div><p>Move from the big picture to the supporting record. Your research tools are already connected.</p></div>
        <div className={s.tools}>
          <Link href="/explore" className={`${s.tool} ${s.toolLarge}`}><div className={s.toolVisual} aria-hidden="true"><div className={s.crosshair}/><span className={s.coord}>STATE → COUNTY → SOURCE</span><div className={s.orbit}/><div className={s.orbitSmall}/><span className={s.mapPoint}/></div><div className={s.toolBody}><span className={s.toolLabel}>THE WIDER VIEW <Arrow diagonal/></span><h3>Find your place in the network.</h3><p>Browse the national explorer by geography and inspect the source coverage available for each area.</p><span className={s.toolAction}>Open national explorer <Arrow/></span></div></Link>
          <div className={s.toolStack}>
            <Link href="/changes" className={s.tool}><div className={s.toolBody}><span className={s.toolLabel}>FILING CHANGES <Arrow diagonal/></span><h3>Plans change.<br/>Keep the context.</h3><p>Compare filing versions and see what changed in the published record.</p><span className={s.toolAction}>Review changes <Arrow/></span></div><div className={s.changeArt} aria-hidden="true"><span/><span/><span/><span/></div></Link>
            <Link href="/coverage" className={s.tool}><div className={s.toolBody}><span className={s.toolLabel}>EVIDENCE & COVERAGE <Arrow diagonal/></span><h3>Know what you know.</h3><p>Check source coverage and uncertainty before you act on a lead.</p><span className={s.toolAction}>See coverage <Arrow/></span></div></Link>
          </div>
        </div>
      </section>

      <section className={s.finalCta} id="go"><h2>Every mile. Connected.</h2><a href="#how-it-works" className={s.primary}>Read how it works <Arrow/></a><p>Network animation is simulated. Overlap analysis uses public utility filings.</p></section>
    </main>
    <footer className={s.footer}><Link href="/" className={s.footerBrand}>GridBridge<span>Every mile. Connected.</span></Link><div><Link href="/map">Project map</Link><Link href="/explore">National explorer</Link><Link href="/coverage">Source coverage</Link></div><p>GridBridge · Built at ShellHacks 2026 for the Sperry Gridlock challenge<br/>Network animation is simulated. Overlap analysis uses public utility filings.</p></footer>
  </div>;
}
