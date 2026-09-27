"use client";

import { useEffect, useRef, type ReactNode } from "react";

const KEY = "gridbridge.legend";

/** The legend folds away once read; the scene controls below it never move. One remembered choice for both scenes.
 *  The browser owns the open state: React renders `open` once and never changes it, so re-renders don't reopen it. */
export function LegendFold({ styles: s, children }: { styles: Record<string, string>; children: ReactNode }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    try {
      if (localStorage.getItem(KEY) === "closed" && ref.current) ref.current.open = false;
    } catch {} // blocked storage: stay open
  }, []);
  return (
    <details ref={ref} className={s.fold} open>
      {/* Persist on the reader's click (Enter/Space click too), not on toggle: the initial open attribute also toggles. */}
      <summary
        className={s.foldSummary}
        onClick={() => {
          try {
            localStorage.setItem(KEY, ref.current?.open ? "closed" : "open");
          } catch {}
        }}
      >
        <span className={s.foldGlyphs} aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        Legend
      </summary>
      {children}
    </details>
  );
}
