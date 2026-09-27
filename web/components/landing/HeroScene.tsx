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

export function HeroScene() {
  const [view, setView] = useState<"road" | "network">("road");
  const [paused, setPaused] = useState(false);
  return (
    <>
      <div className={s.sceneControls} role="group" aria-label="Illustration view">
        <button type="button" aria-pressed={view === "road"} onClick={() => setView("road")}>
          <span>01</span> The road
        </button>
        <button type="button" aria-pressed={view === "network"} onClick={() => setView("network")}>
          <span>02</span> The network
        </button>
      </div>
      <div className={`${s.scene} ${view === "network" ? s.sceneNetwork : ""} ${paused ? s.paused : ""}`}>
        {view === "road" ? <Road paused={paused} /> : <NetworkIllustration />}
      </div>
      <div className={s.sceneCaption}>
        <span className={s.statusDot} />
        {/* Scroll-story beats from GridBridge-reference.html texts.B / texts.C */}
        <span>{view === "road" ? "Same roads." : "One network."}</span>
        <span>{view === "road" ? "Two utilities. Separate filings. Separate trucks." : "GridBridge finds jobs within 25 miles and moves the fleet once."}</span>
      </div>
      <button className={s.pause} type="button" onClick={() => setPaused(!paused)} aria-pressed={paused}>
        {paused ? "Play animation" : "Pause animation"}
      </button>
    </>
  );
}
