"use client";

import { useEffect, useRef } from "react";
import us from "./illustration-us-states.json";
import s from "./landing.module.css";

/** Decorative lower-48 network on Census TIGERweb state outlines. Links are illustrative, not matching output. */
type State = { c: string; d: string; p: [number, number] };

// Long corridors threaded through neighbouring states, so lines read like routes rather than hops.
const routes: string[][] = [
  ["WA", "OR", "CA", "AZ", "NM", "TX", "LA", "MS", "AL", "GA", "SC", "NC", "VA", "PA", "NY", "MA", "ME"],
  ["WA", "ID", "MT", "ND", "MN", "WI", "MI", "OH", "PA"],
  ["CA", "NV", "UT", "CO", "KS", "MO", "IL", "IN", "OH", "WV", "VA"],
  ["TX", "OK", "KS", "NE", "SD", "ND"],
  ["FL", "GA", "TN", "KY", "OH"],
  ["AR", "TN", "NC"],
  ["MT", "WY", "NE", "IA", "IL", "IN"],
];
const hubs = ["CA", "TX", "IL", "GA", "NY", "WA", "CO", "OH", "KS", "TN"];

/** Catmull-Rom spline through the points, as cubic Béziers. */
function smoothPath(pts: [number, number][]) {
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0]},${p2[1]}`;
  }
  return d;
}

// Satellite orbit: a shallow arc over the country, entering west and leaving east.
const ORBIT = "M-60,300 C180,-40 820,-60 1070,250";

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
    // SMIL ignores prefers-reduced-motion, so park the satellite mid-orbit instead.
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      svg.pauseAnimations();
      svg.setCurrentTime(11);
    }
    return () => io.disconnect();
  }, []);

  const states = us.states as State[];
  const at = Object.fromEntries(states.map((st) => [st.c, st.p]));
  const paths = routes.map((r) => ({ id: r.join("-"), d: smoothPath(r.filter((c) => at[c]).map((c) => at[c])) }));
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
        <linearGradient id="sat-beam" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#9fdcff" stopOpacity="0.35" />
          <stop offset="1" stopColor="#9fdcff" stopOpacity="0" />
        </linearGradient>
        {/* Side-view semi facing +x, wheels on the route line: trailer, orange cab, lights. */}
        <g id="us-semi">
          <rect x="-15" y="-11.5" width="19.5" height="8" rx="0.8" fill="#dfe2e7" stroke="#0b0d11" strokeWidth="0.6" />
          <path d="M5,-3.2V-10Q5,-11 6,-11H9L11.6,-7.4V-3.2Z" fill="#ffae42" stroke="#0b0d11" strokeWidth="0.6" />
          <path d="M9.1,-10.3L11,-7.6H9.1Z" fill="#1b2330" />
          <rect x="-15" y="-3.6" width="26.6" height="1.2" fill="#0b0d11" />
          {[-12, -9, 1.2, 7.8].map((x) => (
            <circle key={x} cx={x} cy="-1.5" r="1.5" fill="#0b0d11" stroke="#a3a8b1" strokeWidth="0.5" />
          ))}
          <circle cx="11.4" cy="-4.4" r="0.7" fill="#fff1d6" />
          <rect x="-15.6" y="-5.4" width="0.8" height="1.6" fill="#ff4a3d" />
        </g>
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
            strokeOpacity="0.5"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ animationDelay: `${0.8 + i * 0.25}s`, animationDuration: "2.4s" }}
          />
        ))}
      </g>
      {/* Semis driving each corridor in both directions. */}
      <g className={s.usFleet}>
        {paths.flatMap((p, i) =>
          [0, 1].map((n) => {
            const dur = 22 + (i % 3) * 5;
            return (
              <g key={`${p.id}-${n}`}>
                {/* Stays upright; the second truck drives the route the other way. */}
                <animateMotion
                  dur={`${dur}s`}
                  begin={`-${(i * 3.1 + n * dur * 0.5) % dur}s`}
                  repeatCount="indefinite"
                  path={p.d}
                  {...(n ? { keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" } : {})}
                />
                <use href="#us-semi" transform={n ? "scale(-1.25 1.25)" : "scale(1.25)"} />
              </g>
            );
          }),
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

      <g className={s.usSatellite}>
        <path d={ORBIT} stroke="#9fdcff" strokeOpacity="0.22" strokeWidth="1" strokeDasharray="2 6" />
        <g>
          <animateMotion dur="28s" repeatCount="indefinite" path={ORBIT} />
          {/* Downward sensor beam and ground ping */}
          <path d="M-5,6 L5,6 L26,86 L-26,86Z" fill="url(#sat-beam)" />
          <ellipse className={s.satPing} cx="0" cy="86" rx="26" ry="7" stroke="#9fdcff" strokeOpacity="0.5" />
          <g transform="rotate(-12)">
            <rect x="-24" y="-3.5" width="15" height="7" rx="0.8" fill="#1d3b57" stroke="#5cc8ff" strokeWidth="0.8" />
            <rect x="9" y="-3.5" width="15" height="7" rx="0.8" fill="#1d3b57" stroke="#5cc8ff" strokeWidth="0.8" />
            <path d="M-19,-3.5v7M-14,-3.5v7M14,-3.5v7M19,-3.5v7M-9,0H-6M6,0H9" stroke="#5cc8ff" strokeOpacity="0.6" strokeWidth="0.6" />
            <rect x="-6" y="-5" width="12" height="10" rx="1.6" fill="#d9dde5" />
            <rect x="-6" y="-5" width="12" height="3" rx="1.2" fill="#f4f6fa" />
            <path d="M0,5v3.5" stroke="#d9dde5" strokeWidth="1" />
            <circle cy="9" r="1.6" fill="#ffae42" />
          </g>
        </g>
      </g>

      <text x={W / 2} y={H + 22} fill="#61666e" fontSize="13" letterSpacing="7" textAnchor="middle">
        UNITED STATES
      </text>
    </svg>
  );
}
