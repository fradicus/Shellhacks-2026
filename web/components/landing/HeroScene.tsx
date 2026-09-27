"use client";

import Link from "next/link";
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
        <p>Nearby projects. Evidence for your next conversation.</p>
      </div>
      <div className={s.brandReveal}>
        <span className={s.brandMark}>
          <i />
          <i />
        </span>
        <strong>Common Ground</strong>
        <p>Every mile. Connected.</p>
        <Link href="/time" className={s.brandExplore} aria-label="Explore nearby projects">
          <span>Explore nearby projects</span>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M5 12h14m-6-6 6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
      </div>
      <div className={`${s.scene} ${paused ? s.paused : ""}`}>
        <div className={s.roadLayer}>
          <Road paused={paused} />
        </div>
      </div>
      <button
        className={s.pause}
        type="button"
        data-animation-pause=""
        onClick={(event) => {
          const story = event.currentTarget.closest<HTMLElement>(
            "[data-common-ground-story], [data-gridbridge-story]",
          );
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
