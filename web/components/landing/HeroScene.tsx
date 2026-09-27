"use client";

import { useEffect, useRef, useState } from "react";
import { startRoadScene } from "./road-scene";
import { NetworkIllustration } from "./NetworkIllustration";
import s from "./landing.module.css";

function Road({paused}:{paused:boolean}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => canvas.current ? startRoadScene(canvas.current, paused) : undefined, [paused]);
  return <canvas ref={canvas} className={s.roadCanvas} aria-hidden="true" />;
}

export function HeroScene() {
  const [view,setView] = useState<"road" | "network">("road");
  const [paused,setPaused] = useState(false);
  return <>
    <div className={s.sceneControls} role="group" aria-label="Illustration view">
      <button type="button" aria-pressed={view==="road"} onClick={()=>setView("road")}><span>01</span> The road</button>
      <button type="button" aria-pressed={view==="network"} onClick={()=>setView("network")}><span>02</span> The network</button>
    </div>
    <div className={`${s.scene} ${view === "network" ? s.sceneNetwork : ""} ${paused ? s.paused : ""}`}>
      {view==="road" ? <Road paused={paused} /> : <NetworkIllustration />}
    </div>
    <div className={s.sceneCaption}><span className={s.statusDot} />{view === "road" ? "Separate projects. A shared horizon." : "One region. More possibilities."}<span>Illustrative animation</span></div>
    <button className={s.pause} type="button" onClick={()=>setPaused(!paused)} aria-pressed={paused}>{paused ? "Play animation" : "Pause animation"}</button>
  </>;
}
