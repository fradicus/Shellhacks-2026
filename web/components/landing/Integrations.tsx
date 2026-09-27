"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Mark } from "@/components/nav/Nav";
import s from "./integrations.module.css";

/** Hub-and-spoke of what feeds a worksite plan. Every public source listed here is queried by lib/operations
 * or lib/weather-history; crew, contractor and cost figures are user-entered (components/impact). */
type Node = { id: string; label: string; source: string; x: number; y: number; icon: ReactNode };

const I = (d: ReactNode) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {d}
  </svg>
);

const NODES: Node[] = [
  { id: "weather", label: "Weather", source: "NWS · NOAA", x: 90, y: 70,
    icon: I(<><path d="M7 17h10a4 4 0 0 0 .6-7.96A6 6 0 0 0 6.1 10.5 3.5 3.5 0 0 0 7 17Z" /><path d="M9 20l-1 2M13 20l-1 2M17 20l-1 2" /></>) },
  { id: "water", label: "Water & flood", source: "USGS · FEMA", x: 80, y: 210,
    icon: I(<><path d="M2 9c2 0 2-1.5 4-1.5S8 9 10 9s2-1.5 4-1.5S16 9 18 9s2-1.5 4-1.5" /><path d="M2 15c2 0 2-1.5 4-1.5S8 15 10 15s2-1.5 4-1.5S16 15 18 15s2-1.5 4-1.5" /></>) },
  { id: "soil", label: "Soil", source: "USDA NRCS", x: 90, y: 350,
    icon: I(<><path d="M12 3 2 8l10 5 10-5-10-5Z" /><path d="m2 13 10 5 10-5" /><path d="m2 17.5 10 5 10-5" /></>) },
  { id: "satellite", label: "Satellite", source: "Annual evidence", x: 300, y: 38,
    icon: I(<><path d="m13 7 4-4 4 4-4 4" /><path d="m7 13-4 4 4 4 4-4" /><path d="m9 9 6 6" /><rect x="8.5" y="8.5" width="7" height="7" rx="1" transform="rotate(45 12 12)" /><path d="M16 21a5 5 0 0 0 5-5" /></>) },
  { id: "crews", label: "Crews & contractors", source: "Rates you enter", x: 510, y: 70,
    icon: I(<><path d="M2.5 18h19" /><path d="M4.5 18v-2a7.5 7.5 0 0 1 15 0v2" /><path d="M10 9.2V6.5a2 2 0 0 1 4 0v2.7" /><path d="M8 11.5v6.5M16 11.5v6.5" /></>) },
  { id: "cost", label: "Cost scenarios", source: "Impact scenarios", x: 520, y: 210,
    icon: I(<><circle cx="12" cy="12" r="9.5" /><path d="M15 9.2c-.5-1-1.6-1.6-3-1.6-1.8 0-3 .9-3 2.2 0 3 6 1.6 6 4.5 0 1.3-1.3 2.2-3 2.2-1.5 0-2.6-.7-3.1-1.7M12 6v1.6M12 16.5V18" /></>) },
  { id: "routes", label: "Drive time", source: "Google Routes", x: 510, y: 350,
    icon: I(<><circle cx="6" cy="19" r="2.5" /><circle cx="18" cy="5" r="2.5" /><path d="M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5" /></>) },
  { id: "workzones", label: "Work zones", source: "Washington · WZDx", x: 300, y: 382,
    icon: I(<><path d="M9.5 4h5l4.5 15h-14z" /><path d="M7.6 12h8.8M6.4 16h11.2" /><path d="M3 21h18" /></>) },
];

const CX = 300;
const CY = 210;

/** Orthogonal route from the hub to a node with rounded corners, so lines read like wiring, not spokes. */
function wire(n: Node) {
  if (n.x === CX) return `M${CX},${CY + (n.y < CY ? -34 : 34)} V${n.y + (n.y < CY ? 30 : -30)}`;
  const dir = n.x < CX ? -1 : 1;
  const start = CX + dir * 34;
  const lane = CY + (n.y === CY ? 0 : n.y < CY ? -10 : 10);
  const bendX = CX + dir * 120;
  const endX = n.x - dir * 34;
  if (n.y === CY) return `M${start},${lane} H${endX}`;
  const r = 16;
  const vy = n.y < CY ? -1 : 1;
  return `M${start},${lane} H${bendX - dir * r} Q${bendX},${lane} ${bendX},${lane + vy * r} V${n.y - vy * r} Q${bendX},${n.y} ${bendX + dir * r},${n.y} H${endX}`;
}

export function Integrations() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    el.dataset.armed = "";
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.dataset.inview = "";
          io.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={root} className={s.visual}>
      <svg className={s.wires} viewBox="0 0 600 420" fill="none" aria-hidden="true">
        {NODES.map((n, i) => {
          const d = wire(n);
          return (
            <g key={n.id}>
              <path d={d} className={s.wire} />
              <path d={d} className={s.flow} pathLength={100} style={{ animationDelay: `-${(i * 0.53) % 3.2}s` }} />
            </g>
          );
        })}
      </svg>

      <div className={s.hub}>
        <span className={s.hubRing} />
        <Mark size={34} />
      </div>

      {NODES.map((n, i) => (
        <div
          key={n.id}
          className={`${s.node} ${n.x === CX ? s.nodeSide : ""}`}
          style={{ left: `${(n.x / 600) * 100}%`, top: `${(n.y / 420) * 100}%`, transitionDelay: `${0.15 + i * 0.06}s` }}
        >
          <span className={s.tile}>{n.icon}</span>
          <span className={s.label}>
            {n.label}
            <small>{n.source}</small>
          </span>
        </div>
      ))}
    </div>
  );
}
