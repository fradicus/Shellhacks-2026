"use client";

import { useEffect, useRef } from "react";
import us from "./illustration-us-states.json";
import s from "./landing.module.css";

/** Decorative lower-48 network on Census TIGERweb state outlines. Links are illustrative, not matching output. */
type State = { c: string; d: string; p: [number, number] };

const links: [string, string][] = [
  ["WA", "OR"], ["OR", "CA"], ["CA", "NV"], ["CA", "AZ"], ["NV", "UT"], ["UT", "CO"], ["AZ", "NM"], ["NM", "TX"],
  ["ID", "MT"], ["MT", "ND"], ["WY", "CO"], ["CO", "KS"], ["KS", "MO"], ["NE", "IA"], ["SD", "MN"], ["ND", "MN"],
  ["OK", "TX"], ["TX", "LA"], ["LA", "MS"], ["MS", "AL"], ["AL", "GA"], ["GA", "SC"], ["SC", "NC"], ["NC", "VA"],
  ["GA", "FL"], ["TN", "GA"], ["MO", "TN"], ["AR", "TN"], ["MN", "WI"], ["WI", "IL"], ["IL", "IN"], ["IN", "OH"],
  ["MI", "OH"], ["OH", "PA"], ["KY", "TN"], ["WV", "VA"], ["VA", "MD"], ["MD", "PA"], ["PA", "NY"], ["NY", "MA"],
  ["MA", "ME"], ["IA", "IL"], ["OK", "KS"], ["WA", "ID"],
];
const hubs = ["CA", "TX", "IL", "GA", "NY", "WA", "CO", "SC", "PA", "FL"];

function arc(a: [number, number], b: [number, number]) {
  const [x1, y1] = a, [x2, y2] = b;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const len = Math.hypot(x2 - x1, y2 - y1);
  // Bow each link upward-ish, perpendicular to its direction.
  const nx = -(y2 - y1) / len, ny = (x2 - x1) / len;
  const bend = len * 0.14 * (ny > 0 ? -1 : 1);
  return `M${x1},${y1}Q${(mx + nx * bend).toFixed(1)},${(my + ny * bend).toFixed(1)} ${x2},${y2}`;
}

export function NetworkIllustration() {
  const root = useRef<SVGSVGElement>(null);
  useEffect(() => {
    const svg = root.current;
    if (!svg) return;
    svg.dataset.armed = "";
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          svg.dataset.inview = "";
          io.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    io.observe(svg);
    return () => io.disconnect();
  }, []);

  const states = us.states as State[];
  const at = Object.fromEntries(states.map((st) => [st.c, st.p]));
  const paths = links.filter(([a, b]) => at[a] && at[b]).map(([a, b]) => ({ id: `${a}-${b}`, d: arc(at[a], at[b]) }));
  const { width: W, height: H } = us;

  return (
    <svg ref={root} className={`${s.networkSvg} ${s.usMap}`} viewBox={`-30 -30 ${W + 60} ${H + 60}`} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="us-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#161b24" />
          <stop offset="1" stopColor="#0d1016" />
        </linearGradient>
        <linearGradient id="us-link" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#5cc8ff" />
          <stop offset="1" stopColor="#ffae42" />
        </linearGradient>
        <pattern id="us-dots" width="9" height="9" patternUnits="userSpaceOnUse">
          <circle cx="1.5" cy="1.5" r="0.9" fill="#ffffff" fillOpacity="0.07" />
        </pattern>
        <filter id="us-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
        <filter id="us-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.4" />
        </filter>
        <clipPath id="us-clip">
          {states.map((st) => (
            <path key={st.c} d={st.d} />
          ))}
        </clipPath>
      </defs>

      {/* Country halo */}
      <g className={s.usHalo} filter="url(#us-glow)">
        {states.map((st) => (
          <path key={st.c} d={st.d} stroke="#5cc8ff" strokeOpacity="0.35" strokeWidth="6" />
        ))}
      </g>

      <g className={s.usStates}>
        {states.map((st, i) => (
          <path
            key={st.c}
            d={st.d}
            fill="url(#us-fill)"
            stroke="#2e3644"
            strokeWidth="0.8"
            strokeLinejoin="round"
            style={{ animationDelay: `${(st.p[0] / W) * 0.9 + (i % 5) * 0.03}s` }}
          />
        ))}
      </g>
      <rect x="0" y="0" width={W} height={H} fill="url(#us-dots)" clipPath="url(#us-clip)" />

      <g className={s.usLinks}>
        {paths.map((p, i) => (
          <path
            key={p.id}
            d={p.d}
            pathLength={1}
            stroke="url(#us-link)"
            strokeOpacity="0.45"
            strokeWidth="1.3"
            strokeLinecap="round"
            style={{ animationDelay: `${0.8 + i * 0.035}s` }}
          />
        ))}
      </g>
      <g className={s.usPulses} filter="url(#us-soft)">
        {paths.map((p, i) =>
          i % 2 === 0 ? (
            <path
              key={p.id}
              d={p.d}
              pathLength={1}
              stroke={i % 4 === 0 ? "#ffe2b0" : "#9fdcff"}
              strokeWidth="3.4"
              strokeLinecap="round"
              style={{ animationDelay: `-${(i * 0.37) % 3.2}s`, animationDuration: `${2.6 + (i % 5) * 0.35}s` }}
            />
          ) : null,
        )}
      </g>

      <g className={s.usHubs}>
        {hubs.map((code, i) => {
          const pt = at[code];
          if (!pt) return null;
          return (
            <g key={code} transform={`translate(${pt[0]} ${pt[1]})`} style={{ animationDelay: `${1.4 + i * 0.08}s` }}>
              <circle className={s.usRing} r="5" stroke="#ffe2b0" strokeWidth="1" style={{ animationDelay: `${i * 0.31}s` }} />
              <circle r="7" fill="#ffe2b0" fillOpacity="0.16" />
              <circle r="2.8" fill="#fff6e4" />
            </g>
          );
        })}
      </g>

      <text x={W / 2} y={H + 22} fill="#61666e" fontSize="13" letterSpacing="7" textAnchor="middle">
        UNITED STATES
      </text>
    </svg>
  );
}
