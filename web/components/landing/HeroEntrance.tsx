"use client";

import { useEffect, useState } from "react";
import { HeroScene } from "./HeroScene";
import s from "./landing.module.css";

function Arrow() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 12h15m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type Phase = "truck" | "brand" | "copy" | "ready";

/** Truck-only hold, then brand rise, then tag/CTA, then scene chrome. */
export const HERO_TIMING = {
  truckOnlyMs: 1600,
  brandAtMs: 1600,
  copyAtMs: 2300,
  readyAtMs: 3000,
} as const;

export function HeroEntrance({ fixtureMode }: { fixtureMode: boolean }) {
  const [phase, setPhase] = useState<Phase>("truck");

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      const ready = window.setTimeout(() => setPhase("ready"), 0);
      return () => window.clearTimeout(ready);
    }
    const brand = window.setTimeout(() => setPhase("brand"), HERO_TIMING.brandAtMs);
    const copy = window.setTimeout(() => setPhase("copy"), HERO_TIMING.copyAtMs);
    const ready = window.setTimeout(() => setPhase("ready"), HERO_TIMING.readyAtMs);
    return () => {
      window.clearTimeout(brand);
      window.clearTimeout(copy);
      window.clearTimeout(ready);
    };
  }, []);

  const brandOn = phase !== "truck";
  const copyOn = phase === "copy" || phase === "ready";
  const chromeOn = phase === "ready";

  return (
    <section className={s.hero} aria-labelledby="hero-title" data-hero-phase={phase}>
      <div className={`${s.heroContent} ${brandOn ? s.heroContentOn : s.heroContentOff}`}>
        <h1 id="hero-title" className={`${s.heroBrand} ${brandOn ? s.heroBrandOn : ""}`}>
          GridBridge
        </h1>
        <p className={`${s.heroTag} ${copyOn ? s.heroLayerOn : s.heroLayerOff}`}>Every mile. Connected.</p>
        <div className={`${s.actions} ${copyOn ? s.heroLayerOn : s.heroLayerOff}`}>
          <a href="#how-it-works" className={s.primary} tabIndex={copyOn ? undefined : -1}>
            See how it works <Arrow />
          </a>
        </div>
        <p className={`${s.heroNote} ${copyOn ? s.heroLayerOn : s.heroLayerOff}`}>
          {fixtureMode ? "Sample data available · No account needed" : "Public-source evidence · No account needed"}
        </p>
      </div>
      <p className={s.sr}>
        GridBridge. Every mile. Connected. A truck drives through the title, then the view tilts down to a network of
        trucks across the Southeast United States.
      </p>
      <HeroScene chromeVisible={chromeOn} />
      <a
        href="#how-it-works"
        className={`${s.scrollHint} ${chromeOn ? s.heroLayerOn : s.heroLayerOff}`}
        tabIndex={chromeOn ? undefined : -1}
      >
        Scroll <span aria-hidden="true">↓</span>
      </a>
    </section>
  );
}
