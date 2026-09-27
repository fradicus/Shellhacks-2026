"use client";

import { memo } from "react";
import s from "./history.module.css";

export interface LedgerYear {
  year: number;
  actual: number;
  plan: number;
  other: number;
}

/** The ledger: documented events per year, the selected range, and the year plane. Three native range inputs carry
 * every control, so the keyboard gets the same scrubber the pointer does. */
export const Ledger = memo(function Ledger({
  years,
  from,
  to,
  plane,
  planeLabel,
  onRange,
  onPlane,
  onScrubStart,
}: {
  years: LedgerYear[];
  from: number;
  to: number;
  /** Plane position as a fractional year (2014.5 = early July 2014). */
  plane: number;
  planeLabel: string;
  onRange: (from: number, to: number) => void;
  onPlane: (year: number) => void;
  onScrubStart: () => void;
}) {
  if (!years.length) return null;
  const lo = years[0].year;
  const hi = years[years.length - 1].year + 1;
  const max = Math.max(1, ...years.map((y) => y.actual + y.plan + y.other));
  const pct = (y: number) => `${(((y - lo) / (hi - lo)) * 100).toFixed(3)}%`;
  const w = 100 / years.length;
  return (
    <section className={s.ledger} aria-label="Ledger: documented events per year">
      <div className={s.ledgerHead}>
        <span>Ledger</span>
        <b>
          {from}–{to}
        </b>
        <i>
          <em className={s.kActual} /> actual <em className={s.kPlan} /> plan <em className={s.kOther} /> other
        </i>
      </div>
      <div className={s.ledgerPlot}>
        <svg viewBox={`0 0 100 100`} preserveAspectRatio="none" aria-hidden className={s.bars}>
          {years.map((y, i) => {
            const out = y.year < from || y.year > to;
            const ha = (y.actual / max) * 92;
            const hp = (y.plan / max) * 92;
            const ho = (y.other / max) * 92;
            const x = i * w + w * 0.14;
            const bw = w * 0.72;
            return (
              <g key={y.year} opacity={out ? 0.28 : 1}>
                {ha ? <rect x={x} y={100 - ha} width={bw} height={ha} className={s.barActual} /> : null}
                {hp ? <rect x={x} y={100 - ha - hp} width={bw} height={hp} className={s.barPlan} /> : null}
                {ho ? <rect x={x} y={100 - ha - hp - ho} width={bw} height={ho} className={s.barOther} /> : null}
              </g>
            );
          })}
        </svg>
        <div className={s.window} style={{ left: pct(from), width: `calc(${pct(to + 1)} - ${pct(from)})` }} aria-hidden />
        <div className={s.planeLine} style={{ left: pct(plane) }} aria-hidden>
          <span>{planeLabel}</span>
        </div>
        <input
          type="range"
          className={s.planeInput}
          min={lo}
          max={hi}
          step={1 / 12}
          value={plane}
          aria-label="Year plane: move it to light up events up to a date"
          aria-valuetext={planeLabel}
          onPointerDown={onScrubStart}
          onKeyDown={onScrubStart}
          onChange={(e) => onPlane(Math.min(Math.max(Number(e.target.value), from), to + 1))}
        />
      </div>
      <div className={s.rangeRow}>
        <input
          type="range"
          min={lo}
          max={hi - 1}
          step={1}
          value={from}
          aria-label="Range start year"
          onChange={(e) => onRange(Math.min(Number(e.target.value), to), to)}
        />
        <input
          type="range"
          min={lo}
          max={hi - 1}
          step={1}
          value={to}
          aria-label="Range end year"
          onChange={(e) => onRange(from, Math.max(Number(e.target.value), from))}
        />
      </div>
      <div className={s.ledgerAxis} aria-hidden>
        {years
          .filter((y) => y.year % 5 === 0)
          .map((y) => (
            <span key={y.year} style={{ left: pct(y.year + 0.5) }} data-ten={y.year % 10 === 0 ? "1" : "0"}>
              {y.year}
            </span>
          ))}
      </div>
    </section>
  );
});
