"use client";

import { useEffect, useRef, useState } from "react";
import { startRoadScene } from "./road-scene";
import s from "./landing.module.css";

function Road({ paused }: { paused: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pausedRef = useRef(paused);
  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);
  useEffect(() => (canvas.current ? startRoadScene(canvas.current, () => pausedRef.current) : undefined), []);
  return <canvas ref={canvas} className={s.roadCanvas} aria-hidden="true" />;
}

export function HeroScene() {
  const [paused, setPaused] = useState(false);
  return (
    <>
      <div className={`${s.storyBeat} ${s.storyBeatOne}`} aria-hidden="true">
        <strong>Same roads.</strong>
        <p>Two utilities. Separate plans. Nearby work.</p>
      </div>
      <div className={`${s.storyBeat} ${s.storyBeatTwo}`} aria-hidden="true">
        <strong>One network.</strong>
        <p>Find the overlap. See what connects.</p>
      </div>
      <div className={s.brandReveal} aria-hidden="true">
        <strong>Common Ground</strong>
        <p>Every mile. Connected.</p>
      </div>
      {/* Hidden controls keep the standalone HTML exporter’s adapter stable; map toggle is retired. */}
      <div className={s.sceneControls} role="group" aria-label="Illustration view" hidden>
        <button type="button" aria-pressed="true">
          <span>01</span> The road
        </button>
        <button type="button" aria-pressed="false" tabIndex={-1}>
          <span>02</span> The network
        </button>
      </div>
      <div className={`${s.scene} ${paused ? s.paused : ""}`}>
        <div className={s.roadLayer}>
          <Road paused={paused} />
        </div>
      </div>
      <div className={s.sceneCaption}>
        <span className={s.statusDot} />
        Same roads. One network.
        <span>Illustrative animation</span>
      </div>
      <button
        className={s.pause}
        type="button"
        data-animation-pause=""
        onClick={(event) => {
          const story = event.currentTarget.closest<HTMLElement>("[data-gridbridge-story]");
          if (story) story.dataset.animationPaused = String(!paused);
          setPaused(!paused);
        }}
        aria-pressed={paused}
      >
        {paused ? "Play animation" : "Pause animation"}
      </button>
    </>
  );
}
