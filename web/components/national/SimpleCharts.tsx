import type { MindMapChartSlice } from "@/lib/national/mindmap";
import s from "./national.module.css";

const n = (value: number) => value.toLocaleString("en-US");

const PALETTE = ["#1f6f68", "#2f8f84", "#c47a2c", "#5b6e8c", "#8b4d57", "#4a6b3d", "#6b5b8c", "#3d5a80"];

export function BarChart({
  title,
  slices,
  empty = "No chartable counts in the current filters.",
}: {
  title: string;
  slices: MindMapChartSlice[];
  empty?: string;
}) {
  const max = Math.max(...slices.map((slice) => slice.count), 0);
  return (
    <figure className={s.chartCard} aria-label={title}>
      <figcaption>{title}</figcaption>
      {!slices.length || max === 0 ? (
        <p className={s.chartEmpty}>{empty}</p>
      ) : (
        <ul className={s.barList}>
          {slices.map((slice, index) => (
            <li key={slice.key}>
              <div className={s.barMeta}>
                <span>{slice.label}</span>
                <strong>{n(slice.count)}</strong>
              </div>
              <div className={s.barTrack} aria-hidden="true">
                <span
                  className={s.barFill}
                  style={{
                    width: `${Math.max(4, (slice.count / max) * 100)}%`,
                    background: PALETTE[index % PALETTE.length],
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}

export function DonutChart({
  title,
  slices,
  empty = "No chartable counts in the current filters.",
}: {
  title: string;
  slices: MindMapChartSlice[];
  empty?: string;
}) {
  const total = slices.reduce((sum, slice) => sum + slice.count, 0);
  const radius = 42;
  const stroke = 14;
  const circumference = 2 * Math.PI * radius;
  const arcs = slices.map((slice, index) => {
    const length = total === 0 ? 0 : (slice.count / total) * circumference;
    const offset = slices.slice(0, index).reduce((sum, item) => sum + (total === 0 ? 0 : (item.count / total) * circumference), 0);
    return {
      key: slice.key,
      dash: `${length} ${circumference - length}`,
      offset,
      color: PALETTE[index % PALETTE.length],
    };
  });

  return (
    <figure className={s.chartCard} aria-label={title}>
      <figcaption>{title}</figcaption>
      {!slices.length || total === 0 ? (
        <p className={s.chartEmpty}>{empty}</p>
      ) : (
        <div className={s.donutWrap}>
          <svg viewBox="0 0 120 120" className={s.donut} role="img" aria-label={`${title}: ${n(total)} projects`}>
            <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(18,58,56,0.08)" strokeWidth={stroke} />
            {arcs.map((arc) => (
              <circle
                key={arc.key}
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={arc.color}
                strokeWidth={stroke}
                strokeDasharray={arc.dash}
                strokeDashoffset={-arc.offset}
                transform="rotate(-90 60 60)"
              />
            ))}
            <text x="60" y="58" textAnchor="middle" className={s.donutValue}>{n(total)}</text>
            <text x="60" y="74" textAnchor="middle" className={s.donutUnit}>projects</text>
          </svg>
          <ul className={s.donutLegend}>
            {slices.map((slice, index) => (
              <li key={slice.key}>
                <span className={s.swatch} style={{ background: PALETTE[index % PALETTE.length] }} aria-hidden="true" />
                <span>{slice.label}</span>
                <strong>{n(slice.count)}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </figure>
  );
}
