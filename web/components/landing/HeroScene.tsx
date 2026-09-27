"use client";

import { useEffect, useRef, useState } from "react";
import { startRoadScene } from "./road-scene";
import { NetworkIllustration } from "./NetworkIllustration";
import s from "./landing.module.css";

function Road({ paused }: { paused: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pausedRef = useRef(paused);
  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);
  useEffect(() => {
    if (!canvas.current) return;
    return startRoadScene(canvas.current, () => pausedRef.current);
  }, []);
  return <canvas ref={canvas} className={s.roadCanvas} aria-hidden="true" />;
}

export function HeroScene({ chromeVisible = true }: { chromeVisible?: boolean }) {
  const [view, setView] = useState<"road" | "network">("road");
  const [paused, setPaused] = useState(false);
  const chrome = chromeVisible ? s.heroLayerOn : s.heroLayerOff;
  return (
    <>
      <div className={`${s.sceneControls} ${chrome}`} role="group" aria-label="Illustration view">
        <button type="button" aria-pressed={view === "road"} onClick={() => setView("road")} tabIndex={chromeVisible ? undefined : -1}>
          <span>01</span> The road
        </button>
        <button type="button" aria-pressed={view === "network"} onClick={() => setView("network")} tabIndex={chromeVisible ? undefined : -1}>
          <span>02</span> The network
        </button>
      </div>
      <div className={`${s.scene} ${view === "network" ? s.sceneNetwork : ""} ${paused ? s.paused : ""}`}>
        {view === "road" ? <Road paused={paused} /> : <NetworkIllustration />}
      </div>
      <div className={`${s.sceneCaption} ${chrome}`}>
        <span className={s.statusDot} />
        {/* Scroll-story beats from GridBridge-reference.html texts.B / texts.C */}
        <span>{view === "road" ? "Same roads." : "One network."}</span>
        <span>{view === "road" ? "Two utilities. Separate filings. Separate trucks." : "GridBridge finds jobs within 25 miles and moves the fleet once."}</span>
      </div>
      <button className={`${s.pause} ${chrome}`} type="button" onClick={() => setPaused(!paused)} aria-pressed={paused} tabIndex={chromeVisible ? undefined : -1}>
        {paused ? "Play animation" : "Pause animation"}
      </button>
    </>
  );
}
