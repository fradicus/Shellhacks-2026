import bounds from "./illustration-us-bounds.json";
import s from "./landing.module.css";

/** Decorative continental US from Census state bounds. Not used by matching. */
const WEST = -124.8;
const EAST = -66.9;
const SOUTH = 24.5;
const NORTH = 49.4;
const VW = 1000;
const VH = 620;

function project(lon: number, lat: number): [number, number] {
  const x = ((lon - WEST) / (EAST - WEST)) * VW;
  const y = ((NORTH - lat) / (NORTH - SOUTH)) * VH;
  return [x, y];
}

const corridors: [string, string][] = [
  ["WA", "OR"],
  ["OR", "CA"],
  ["CA", "AZ"],
  ["AZ", "NM"],
  ["NM", "TX"],
  ["TX", "LA"],
  ["LA", "MS"],
  ["MS", "AL"],
  ["AL", "GA"],
  ["GA", "SC"],
  ["SC", "NC"],
  ["NC", "VA"],
  ["VA", "MD"],
  ["MD", "PA"],
  ["PA", "NY"],
  ["NY", "MA"],
  ["MT", "ND"],
  ["ND", "MN"],
  ["MN", "WI"],
  ["WI", "IL"],
  ["IL", "IN"],
  ["IN", "OH"],
  ["OH", "PA"],
  ["CO", "KS"],
  ["KS", "MO"],
  ["MO", "TN"],
  ["TN", "GA"],
];

type StateBound = { c: string; w: number; e: number; s: number; n: number };

export function NetworkIllustration() {
  const states = bounds.states as StateBound[];
  const centers = Object.fromEntries(
    states.map((st) => {
      const [x1, y1] = project(st.w, st.n);
      const [x2, y2] = project(st.e, st.s);
      return [st.c, [(x1 + x2) / 2, (y1 + y2) / 2] as [number, number]];
    }),
  );

  return (
    <svg className={s.networkSvg} viewBox={`-20 -20 ${VW + 40} ${VH + 40}`} fill="none" aria-hidden="true">
      {states.map((st) => {
        const [x1, y1] = project(st.w, st.n);
        const [x2, y2] = project(st.e, st.s);
        const w = Math.max(2, x2 - x1);
        const h = Math.max(2, y2 - y1);
        return (
          <rect
            key={st.c}
            x={x1}
            y={y1}
            width={w}
            height={h}
            rx={2}
            fill="#12151c"
            stroke="#2a303a"
            strokeWidth="0.9"
          />
        );
      })}
      {corridors.map(([a, b], i) => {
        const from = centers[a];
        const to = centers[b];
        if (!from || !to) return null;
        return (
          <line
            key={`${a}-${b}-${i}`}
            x1={from[0]}
            y1={from[1]}
            x2={to[0]}
            y2={to[1]}
            stroke="#ffe2b0"
            strokeOpacity="0.28"
            strokeWidth="1.4"
          />
        );
      })}
      {corridors.slice(0, 8).map(([a, b], i) => {
        const from = centers[a];
        const to = centers[b];
        if (!from || !to) return null;
        return (
          <line
            className={s.networkFlow}
            style={{ animationDelay: `-${i * 1.5}s` }}
            key={`flow-${a}-${b}`}
            x1={from[0]}
            y1={from[1]}
            x2={to[0]}
            y2={to[1]}
            stroke="#ffe2b0"
            strokeWidth="2.2"
            strokeDasharray="4 160"
          />
        );
      })}
      {["CA", "TX", "IL", "GA", "NY", "WA"].map((code) => {
        const pt = centers[code];
        if (!pt) return null;
        return <circle key={code} cx={pt[0]} cy={pt[1]} r="3.2" fill="#e5f3ff" />;
      })}
      <text x={VW / 2} y={VH - 8} fill="#61666e" fontSize="14" letterSpacing="6" textAnchor="middle">
        UNITED STATES
      </text>
    </svg>
  );
}
