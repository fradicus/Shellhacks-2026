"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap } from "maplibre-gl";
import Link from "next/link";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { intersects, milesBetween, type HistoryEvent, type HistoryProject, type Meaning } from "@/lib/history/events";
import type { HistoryPayload } from "@/lib/history/server";
import { CANDIDATE_COLOR } from "@/components/time/nationalProjects";
import type { Emphasis, HistoryItem, HistoryLayer, LabelSpec, Projected } from "./historyLayer";
import { Ledger, type LedgerYear } from "./Ledger";
import s from "./history.module.css";

const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
// Identity colours exactly as on /time: the utilities, and the national records.
const COLOR: Record<HistoryProject["identity"], string> = { DESC: "#5cc8ff", GPC: "#ffae42", unknown: "#8b93a7", national: "#88dbc1" };
const DAY_MS = 86_400_000;
const YEAR_D = 365.25;
const NEAR_MI = 25;
const MEANINGS: { v: Meaning | "all"; label: string; help: string }[] = [
  { v: "all", label: "All", help: "Every documented event" },
  { v: "actual", label: "Built", help: "Documented actual in-service dates" },
  { v: "plan", label: "Planned", help: "Documented plan dates: projected, required, revised, filed" },
  { v: "other", label: "Other", help: "Other documented events, such as certifications" },
];
const MEANING_WORD: Record<Meaning, string> = { actual: "Actual", plan: "Plan", other: "Documented" };

const dayOfIso = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d) / DAY_MS;
};
const yearStart = (y: number) => Date.UTC(y, 0, 1) / DAY_MS;
const fracYear = (day: number) => {
  const y = new Date(day * DAY_MS).getUTCFullYear();
  return y + (day - yearStart(y)) / (yearStart(y + 1) - yearStart(y));
};
const dayOfFrac = (fy: number) => {
  const y = Math.floor(fy);
  return yearStart(y) + (fy - y) * (yearStart(y + 1) - yearStart(y));
};
const monthLabel = (day: number) =>
  new Date(day * DAY_MS).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
const fmtDay = (day: number) =>
  new Date(day * DAY_MS).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
function when(e: HistoryEvent): string {
  if (e.from === null) return e.value ? `“${e.value}”, date not exact` : "date unknown";
  if (e.precision === "day") return fmtDay(e.from);
  if (e.precision === "month") return `${monthLabel(e.from)} · month only`;
  return `${new Date(e.from * DAY_MS).getUTCFullYear()} · year only`;
}
const signed = (d: number) => `${d > 0 ? "+" : d < 0 ? "−" : ""}${Math.abs(d).toLocaleString("en-US")}`;
const color = (p: HistoryProject) => (p.candidate ? CANDIDATE_COLOR : COLOR[p.identity]);

function bearingDeg(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180;
  const y = Math.sin((b.lon - a.lon) * r) * Math.cos(b.lat * r);
  const x = Math.cos(a.lat * r) * Math.sin(b.lat * r) - Math.sin(a.lat * r) * Math.cos(b.lat * r) * Math.cos((b.lon - a.lon) * r);
  return (Math.atan2(y, x) * 180) / Math.PI;
}

function overviewPadding(el: HTMLElement | null) {
  const w = el?.clientWidth ?? 1400;
  const h = el?.clientHeight ?? 800;
  return w <= 860
    ? { top: 90, bottom: Math.round(h * 0.52), left: 16, right: 16 }
    : { top: 70, bottom: 190, left: Math.min(460, w * 0.34), right: 300 };
}

/** One row per project in the list: what its latest in-range event says, and its plan -> actual difference. */
interface Row {
  p: HistoryProject;
  events: HistoryEvent[];
  latest: HistoryEvent | null;
  miles: number | null;
}

const EventGlyph = ({ e }: { e: Pick<HistoryEvent, "meaning" | "precision"> }) => (
  <i className={s.glyph} data-m={e.meaning} data-span={e.precision === "month" || e.precision === "year" ? "1" : "0"} aria-hidden />
);

const ProjectList = memo(function ProjectList({
  rows,
  selected,
  onSelect,
  onPreview,
}: {
  rows: Row[];
  selected: string | null;
  onSelect: (key: string) => void;
  onPreview: (key: string | null) => void;
}) {
  return (
    <ol className={s.list}>
      {rows.map(({ p, latest, events, miles }) => (
        <li key={p.key}>
          <button
            type="button"
            style={{ ["--c" as string]: color(p) }}
            aria-pressed={p.key === selected}
            onClick={() => onSelect(p.key)}
            onMouseEnter={() => onPreview(p.key)}
            onMouseLeave={() => onPreview(null)}
            onFocus={() => onPreview(p.key)}
            onBlur={() => onPreview(null)}
          >
            <span className={s.rowName}>
              <i style={{ background: color(p) }} />
              {p.name}
            </span>
            <span className={s.rowSub}>
              {latest ? (
                <>
                  <EventGlyph e={latest} /> {latest.label} · {when(latest)}
                </>
              ) : (
                "No dated event"
              )}
              {events.length > 1 ? ` · ${events.length} events` : ""}
            </span>
            <span className={s.rowNum}>
              {miles !== null ? <b>{miles.toFixed(1)} mi</b> : null}
              {p.thread ? <em data-late={p.thread.days > 0 ? "1" : "0"}>{signed(p.thread.days)} d</em> : null}
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
});

/** The selected project's documented events on a flat, readable track, with its plan -> actual bracket. */
function EventTrack({ p }: { p: HistoryProject }) {
  const dated = p.events.filter((e) => e.from !== null);
  if (!dated.length) return null;
  const lo = Math.min(...dated.map((e) => e.from!));
  const hi = Math.max(...dated.map((e) => e.to!));
  const pad = Math.max((hi - lo) * 0.12, 20);
  const x = (d: number) => 6 + ((d - (lo - pad)) / (hi - lo + 2 * pad)) * 288;
  const t = p.thread;
  const a = t ? dated.find((e) => e.id === t.from) : undefined;
  const b = t ? dated.find((e) => e.id === t.to) : undefined;
  return (
    <svg className={s.track} viewBox="0 0 300 64" role="img" aria-label={`Documented events from ${fmtDay(lo)} to ${fmtDay(hi - 1)}`}>
      <line x1="6" x2="294" y1="40" y2="40" className={s.trackAxis} />
      {a && b ? (
        <g className={s.trackBracket} data-late={t!.days > 0 ? "1" : "0"}>
          <line x1={x(a.from!)} x2={x(b.from!)} y1="16" y2="16" />
          <line x1={x(a.from!)} x2={x(a.from!)} y1="12" y2="34" />
          <line x1={x(b.from!)} x2={x(b.from!)} y1="12" y2="34" />
          <text x={(x(a.from!) + x(b.from!)) / 2} y="10" textAnchor="middle">
            {signed(t!.days)} days
          </text>
        </g>
      ) : null}
      {dated.map((e) =>
        e.to! - e.from! > 1 ? (
          <rect key={e.id} x={x(e.from!)} width={Math.max(x(e.to!) - x(e.from!), 3)} y="36" height="8" rx="3" className={s.trackSpan} />
        ) : (
          <g key={e.id} transform={`translate(${x(e.from!)} 40)`} className={s.trackMark} data-m={e.meaning} data-old={e.superseded ? "1" : "0"}>
            {e.meaning === "actual" ? <circle r="4.6" /> : e.meaning === "plan" ? <circle r="4.2" className={s.hollow} /> : <rect x="-4" y="-4" width="8" height="8" />}
          </g>
        ),
      )}
      <text x="6" y="60" className={s.trackTick}>
        {fmtDay(lo)}
      </text>
      <text x="294" y="60" textAnchor="end" className={s.trackTick}>
        {fmtDay(hi - 1)}
      </text>
    </svg>
  );
}

export type HistoryParams = Record<"origin" | "project" | "from" | "to" | "at" | "show" | "source" | "q", string | null>;

export function HistoryView({ data, initial }: { data: HistoryPayload; initial: HistoryParams }) {
  const { projects, analysisDate, national } = data;
  const analysisDay = dayOfIso(analysisDate);
  const analysisYear = new Date(analysisDay * DAY_MS).getUTCFullYear();
  const byKey = useMemo(() => new Map(projects.map((p) => [p.key, p])), [projects]);
  const located = useMemo(() => projects.filter((p) => p.center), [projects]);

  // The ledger's full extent: every located dated event, whatever the filters. The default window starts where the
  // record gets going (the 2nd percentile year), so one early certificate doesn't stretch the axis; the ledger still
  // shows and reaches every earlier year.
  const [minYear, maxYear, startYear] = useMemo(() => {
    const ys = located
      .flatMap((p) => p.events.filter((e) => e.from !== null).map((e) => new Date(e.from! * DAY_MS).getUTCFullYear()))
      .sort((a, b) => a - b);
    if (!ys.length) return [analysisYear - 10, analysisYear, analysisYear - 10];
    const lo = Math.max(ys[0], analysisYear - 40);
    return [lo, Math.max(ys[ys.length - 1], analysisYear), Math.max(lo, Math.min(ys[Math.floor(ys.length * 0.02)], analysisYear))];
  }, [located, analysisYear]);

  // --- state, restored from the URL (read on the server, so the first render is already the linked view) -------------
  const yr = (v: string | null) => (v && /^\d{4}$/.test(v) ? Math.min(Math.max(+v, minYear), maxYear) : null);
  const [range, setRange] = useState<[number, number]>(() => {
    const f = yr(initial.from) ?? startYear;
    return [f, Math.max(yr(initial.to) ?? analysisYear, f)];
  });
  const [planeDay, setPlaneDay] = useState(() => {
    const atDay = initial.at && /^\d{4}-\d{2}$/.test(initial.at) ? dayOfIso(`${initial.at}-01`) : null;
    return Math.min(Math.max(atDay ?? analysisDay, yearStart(range[0])), yearStart(range[1] + 1));
  });
  const [show, setShow] = useState<Meaning | "all">(() =>
    initial.show === "actual" || initial.show === "plan" || initial.show === "other" ? initial.show : "all",
  );
  const [source, setSource] = useState(initial.source ?? "");
  const [query, setQuery] = useState(initial.q ?? "");
  const [originKey, setOriginKey] = useState<string | null>(initial.origin);
  const [selected, setSelected] = useState<string | null>(initial.project);
  const [hover, setHover] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [flat, setFlat] = useState(false);
  const [yearPx, setYearPx] = useState(14);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);

  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const layerRef = useRef<HistoryLayer | null>(null);
  const labelEls = useRef(new Map<string, HTMLElement>());
  const reduced = useRef(false);
  const rippleRef = useRef(false);
  const playRef = useRef<number | null>(null);
  const fitPx = useRef(14);

  useEffect(() => {
    const id = window.setTimeout(() => {
      const u = new URL(window.location.href);
      const set = (k: string, v: string | null) => (v ? u.searchParams.set(k, v) : u.searchParams.delete(k));
      set("origin", originKey);
      set("project", selected);
      set("from", range[0] !== startYear ? String(range[0]) : null);
      set("to", range[1] !== analysisYear ? String(range[1]) : null);
      set("at", Math.abs(planeDay - analysisDay) > 20 ? new Date(planeDay * DAY_MS).toISOString().slice(0, 7) : null);
      set("show", show === "all" ? null : show);
      set("source", source || null);
      set("q", query.trim() || null);
      window.history.replaceState(window.history.state, "", u);
    }, 250);
    return () => window.clearTimeout(id);
  }, [originKey, selected, range, planeDay, show, source, query, startYear, analysisYear, analysisDay]);

  // --- the window and its facts -----------------------------------------------------------------------------------
  const lo = yearStart(range[0]);
  const hi = yearStart(range[1] + 1);
  const toYears = useCallback((day: number) => (day - lo) / YEAR_D, [lo]);
  const topYears = (hi - lo) / YEAR_D;
  const planeYears = toYears(planeDay);
  const origin = originKey ? byKey.get(originKey) : undefined;

  const sources = useMemo(() => {
    const m = new Map<string, string>();
    for (const p of projects) if (!m.has(p.source_id)) m.set(p.source_id, p.source_title ?? p.source_id);
    return [...m].sort((a, b) => a[1].localeCompare(b[1]));
  }, [projects]);

  // Filters other than the date window: meaning, source and literal text. The ledger counts through these.
  const matches = useCallback(
    (p: HistoryProject) => {
      if (source && p.source_id !== source) return false;
      const q = query.trim().toLowerCase();
      return !q || p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q) || (p.owner ?? "").toLowerCase().includes(q);
    },
    [source, query],
  );
  const kept = useCallback((e: HistoryEvent) => show === "all" || e.meaning === show, [show]);

  const rows: Row[] = useMemo(() => {
    const out: Row[] = [];
    for (const p of located) {
      if (!matches(p)) continue;
      const events = p.events.filter((e) => kept(e) && intersects(e, lo, hi));
      if (!events.length) continue;
      const latest = events.reduce((a, b) => ((b.from ?? -Infinity) > (a.from ?? -Infinity) ? b : a));
      out.push({ p, events, latest, miles: origin?.center && p.center ? milesBetween(origin.center, p.center) : null });
    }
    // Most recent *past* event first: History leads with what has happened; rows with only later dates follow.
    const past = (r: Row) => Math.max(-Infinity, ...r.events.filter((e) => e.from! <= analysisDay).map((e) => e.from!));
    return out.sort((a, b) => past(b) - past(a) || (b.latest?.from ?? 0) - (a.latest?.from ?? 0) || a.p.name.localeCompare(b.p.name));
  }, [located, matches, kept, lo, hi, origin, analysisDay]);

  const near = useMemo(
    () => (origin?.center ? rows.filter((r) => r.p.key !== origin.key && r.miles !== null && r.miles <= NEAR_MI).sort((a, b) => a.miles! - b.miles!) : []),
    [rows, origin],
  );
  const undated = useMemo(() => located.filter((p) => matches(p) && !p.events.some((e) => e.from !== null)), [located, matches]);
  const unlocated = useMemo(() => projects.filter((p) => !p.center && matches(p)), [projects, matches]);

  const ledger: LedgerYear[] = useMemo(() => {
    const years = new Map<number, LedgerYear>();
    for (let y = minYear; y <= maxYear; y++) years.set(y, { year: y, actual: 0, plan: 0, other: 0 });
    for (const p of located)
      if (matches(p))
        for (const e of p.events) {
          if (e.from === null || !kept(e)) continue;
          const row = years.get(new Date(e.from * DAY_MS).getUTCFullYear());
          if (row) row[e.meaning]++;
        }
    return [...years.values()];
  }, [located, matches, kept, minYear, maxYear]);

  const eventCount = rows.reduce((n, r) => n + r.events.length, 0);
  const builtRows = rows.flatMap((r) => r.events.filter((e) => e.meaning === "actual"));
  const builtByPlane = builtRows.filter((e) => e.from! <= planeDay).length;
  // The record's own verdict: documented actual dates against the same row's required date.
  const required = rows.filter((r) => r.p.thread && r.events.some((e) => e.id === r.p.thread!.from && e.field === "RequiredDate") && r.events.some((e) => e.id === r.p.thread!.to));
  const early = required.filter((r) => r.p.thread!.days < 0).length;

  const items: HistoryItem[] = useMemo(
    () =>
      rows.map(({ p, events }) => ({
        key: p.key,
        color: color(p),
        lng: p.center!.lon,
        lat: p.center!.lat,
        glyphs: events.map((e) => ({
          id: e.id,
          meaning: e.meaning,
          z0: Math.max(0, toYears(e.from!)),
          z1: e.to! - e.from! > 1 ? Math.min(toYears(e.to!), topYears) : Math.max(0, toYears(e.from!)),
          superseded: !!e.superseded,
        })),
        thread: (() => {
          const t = p.thread;
          const a = t && events.find((e) => e.id === t.from);
          const b = t && events.find((e) => e.id === t.to);
          return a && b ? { z0: toYears(a.from!), z1: toYears(b.from!) } : null;
        })(),
      })),
    [rows, toYears, topYears],
  );

  const bbox = useMemo(() => {
    const pts = (origin?.center ? [origin, ...near.map((r) => r.p)] : rows.map((r) => r.p)).map((p) => p.center!);
    if (origin?.center && pts.length === 1) {
      const d = NEAR_MI / 69.05;
      return [origin.center.lon - d * 1.3, origin.center.lat - d, origin.center.lon + d * 1.3, origin.center.lat + d] as const;
    }
    return pts.length
      ? ([Math.min(...pts.map((c) => c.lon)), Math.min(...pts.map((c) => c.lat)), Math.max(...pts.map((c) => c.lon)), Math.max(...pts.map((c) => c.lat))] as const)
      : ([-80, 36, -69, 45] as const);
  }, [rows, near, origin]);

  const project = selected ? byKey.get(selected) : undefined;

  // Fit the vertical scale so the whole window stands about a third of the stage tall.
  const fit = useCallback((years: number) => {
    const h = container.current?.clientHeight ?? 800;
    fitPx.current = Math.max(4, Math.min(60, Math.round((h * 0.34) / Math.max(years, 1))));
    setYearPx(fitPx.current);
  }, []);

  // --- the map, created once --------------------------------------------------------------------------------------
  useEffect(() => {
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const [ml, { createHistoryLayer }] = await Promise.all([import("maplibre-gl"), import("./historyLayer")]);
        if (cancelled || !container.current) return;
        ml.setWorkerUrl(`https://cdn.jsdelivr.net/npm/maplibre-gl@${ml.getVersion()}/dist/maplibre-gl-worker.mjs`);
        map = new ml.Map({
          container: container.current,
          style: STYLE_URL,
          bounds: [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[3]],
          ],
          fitBoundsOptions: { padding: overviewPadding(container.current) },
          // History faces the other way round from /time: the same instrument, seen from its other side.
          bearing: 18,
          pitch: 56,
          attributionControl: { compact: true },
          maxPitch: 78,
          canvasContextAttributes: { antialias: true },
        });
        mapRef.current = map;
        map.on("error", (e) => {
          if (/fetch|load|tile|style|NetworkError|Failed/i.test(e.error?.message ?? ""))
            setFailure("Basemap tiles failed to load. The ledger, the project list and every source still work.");
        });
        map.on("load", () => {
          if (!map) return;
          map.setProjection({ type: "mercator" });
          // An archive, not a forecast: warm the land and quieten the labels. Water stays cool for orientation.
          for (const l of map.getStyle().layers ?? []) {
            if (l.type === "background") map.setPaintProperty(l.id, "background-color", "#0d0b09");
            else if (l.type === "fill" && !/water/i.test(l.id)) map.setPaintProperty(l.id, "fill-color", "#15120e");
            else if (l.type === "symbol") {
              if (/poi|transit|aeroway|housenum|road_shield|highway-shield/i.test(l.id)) map.setLayoutProperty(l.id, "visibility", "none");
              else {
                map.setPaintProperty(l.id, "text-opacity", 0.5);
                map.setPaintProperty(l.id, "text-color", "#b7a88f");
              }
            }
          }
          const layer = createHistoryLayer(ml, {
            yearPx: fitPx.current,
            onFrame: (pos: Projected) => {
              for (const [id, p] of pos) {
                const el = labelEls.current.get(id);
                if (!el) continue;
                el.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
                el.dataset.on = p.on ? "1" : "0";
              }
              // The plan -> actual bracket lives in screen space, beside the selected pillar.
              const a = pos.get("th-a");
              const b = pos.get("th-b");
              const br = labelEls.current.get("bracket");
              if (br && a && b) {
                const top = Math.min(a.y, b.y);
                br.style.transform = `translate3d(${(Math.max(a.x, b.x) + 16).toFixed(1)}px, ${top.toFixed(1)}px, 0)`;
                br.style.height = `${Math.max(Math.abs(a.y - b.y), 2).toFixed(1)}px`;
                br.dataset.on = a.on && b.on ? "1" : "0";
              }
            },
          });
          layerRef.current = layer;
          if (process.env.NODE_ENV !== "production") (window as unknown as { __hv: unknown }).__hv = { map, layer };
          map.addLayer(layer.layer);
          fit((yearStart(range[1] + 1) - yearStart(range[0])) / YEAR_D);
          setReady(true);
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        setFailure(
          /webgl/i.test(msg) || !msg
            ? "3D view unavailable: this browser has no WebGL2. The ledger, the project list and every source still work."
            : `3D view unavailable (${msg.slice(0, 120)}). The ledger and the project list still work.`,
        );
      }
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
    // The map is created once; data flows in through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  // Data in. The axis grows once on arrival (no camera flight); after that, changes apply at once.
  const grown = useRef(false);
  useEffect(() => {
    const layer = layerRef.current;
    if (!ready || !layer) return;
    layer.setItems(items, topYears, toYears(analysisDay));
    if (!grown.current) {
      grown.current = true;
      layer.setHeight(flat ? 0 : 1, reduced.current ? 0 : 1800);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, items, topYears]);

  useEffect(() => {
    layerRef.current?.setPlane(planeYears, rippleRef.current && !reduced.current);
  }, [planeYears, ready]);

  useEffect(() => {
    layerRef.current?.setYearPx(yearPx);
  }, [yearPx, ready]);

  useEffect(() => {
    if (!ready) return;
    layerRef.current?.setOrigin(origin?.center ? { lng: origin.center.lon, lat: origin.center.lat } : null);
  }, [ready, origin, items]);

  const emphasis = useCallback(
    (key: string): Emphasis => {
      if (selected) return key === selected ? "sel" : key === hover ? "hot" : "dim";
      if (preview) return key === preview ? "hot" : "dim";
      if (origin?.center && near.length) return near.some((r) => r.p.key === key) ? "hot" : key === hover ? "hot" : "dim";
      return key === hover ? "hot" : "normal";
    },
    [selected, hover, preview, origin, near],
  );
  const rulerAt = useMemo(() => ({ lng: bbox[2] + (bbox[2] - bbox[0]) * 0.06 + 0.15, lat: bbox[1] + (bbox[3] - bbox[1]) * 0.4 }), [bbox]);
  useEffect(() => {
    if (!ready) return;
    layerRef.current?.setFocus({ emphasis, ruler: rulerAt });
  }, [ready, emphasis, rulerAt, items]);

  // --- labels on the scene ----------------------------------------------------------------------------------------
  const sel = project?.center ? project : undefined;
  const selItem = sel ? items.find((i) => i.key === sel.key) : undefined;
  const labelSpecs: (LabelSpec & { text: React.ReactNode; kind: string })[] = [];
  if (!flat) {
    const step = topYears > 30 ? 10 : topYears > 12 ? 5 : topYears > 5 ? 2 : 1;
    // Round years on the ruler (2005, 2010 ...), plus the window's own start.
    labelSpecs.push({ id: "y0", ...rulerAt, years: 0, kind: "tick", text: range[0] });
    for (let y = Math.ceil((range[0] + 1) / step) * step; y <= range[1] + 1; y += step)
      if (y - range[0] >= step / 2) labelSpecs.push({ id: `y${y}`, ...rulerAt, years: toYears(yearStart(y)), kind: "tick", text: y });
    labelSpecs.push({ id: "plane", ...rulerAt, years: planeYears, kind: "plane", text: <>Plane · {monthLabel(planeDay)}</> });
    const ty = toYears(analysisDay);
    if (ty >= 0 && ty <= topYears && Math.abs(ty - planeYears) > 0.6)
      labelSpecs.push({ id: "today", ...rulerAt, years: ty, kind: "today", text: <>Analysis date · {fmtDay(analysisDay)}</> });
  }
  if (sel && selItem) {
    const top = Math.max(...selItem.glyphs.map((g) => g.z1), 0);
    labelSpecs.push({ id: "sel", lng: sel.center!.lon, lat: sel.center!.lat, years: flat ? 0 : top, kind: "bead", text: sel.name });
    if (selItem.thread && !flat) {
      labelSpecs.push({ id: "th-a", lng: sel.center!.lon, lat: sel.center!.lat, years: selItem.thread.z0, kind: "anchor", text: null });
      labelSpecs.push({ id: "th-b", lng: sel.center!.lon, lat: sel.center!.lat, years: selItem.thread.z1, kind: "anchor", text: null });
    }
  }
  if (origin?.center)
    labelSpecs.push({ id: "origin", lng: origin.center.lon, lat: origin.center.lat, years: flat ? 0 : topYears + 0.3, kind: "origin", text: <>From Overlaps · {origin.name}</> });
  const hovered = hover && hover !== selected ? byKey.get(hover) : undefined;
  const hoverItem = hovered ? items.find((i) => i.key === hovered.key) : undefined;
  if (hovered?.center && hoverItem) {
    const r = rows.find((x) => x.p.key === hovered.key);
    labelSpecs.push({
      id: "hover",
      lng: hovered.center.lon,
      lat: hovered.center.lat,
      years: flat ? 0 : Math.max(...hoverItem.glyphs.map((g) => g.z1), 0),
      kind: "hover",
      text: (
        <>
          <b>
            <i style={{ background: color(hovered) }} />
            {hovered.name}
          </b>
          <span>{r?.latest ? `${r.latest.label} · ${when(r.latest)}` : hovered.owner}</span>
        </>
      ),
    });
  }
  const labelKey = labelSpecs.map((l) => `${l.id}:${l.lng.toFixed(4)}:${l.lat.toFixed(4)}:${l.years.toFixed(4)}`).join("|");
  useEffect(() => {
    layerRef.current?.setLabels(labelSpecs);
    // labelKey captures every field the layer reads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labelKey, ready]);

  // --- camera, selection, pointer, keys ---------------------------------------------------------------------------
  const overview = useCallback(() => {
    setSelected(null);
    setYearPx(fitPx.current);
    const map = mapRef.current;
    if (!map) return;
    const cam = map.cameraForBounds(
      [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[3]],
      ],
      { padding: overviewPadding(container.current), bearing: 18 },
    );
    if (cam) map.flyTo({ ...cam, bearing: 18, pitch: flat ? 0 : 56, duration: reduced.current ? 0 : 1500 });
  }, [bbox, flat]);

  const select = useCallback(
    (key: string | null) => {
      setSelected(key);
      const p = key ? byKey.get(key) : undefined;
      const it = key ? items.find((i) => i.key === key) : undefined;
      const map = mapRef.current;
      if (!p?.center || !map) return;
      // Raise the scale so the selected record's dated events fill about half the stage above its foot.
      const top = it ? Math.max(...it.glyphs.map((g) => g.z1), 0.5) : topYears;
      const h = container.current?.clientHeight ?? 800;
      const mobile = (container.current?.clientWidth ?? 1400) <= 860;
      setYearPx(Math.max(4, Math.min(60, Math.round((h * (mobile ? 0.26 : 0.42)) / top))));
      const brg = origin?.center && origin.key !== p.key ? bearingDeg(origin.center, p.center) - 90 : map.getBearing();
      map.flyTo({
        center: [p.center.lon, p.center.lat],
        zoom: Math.max(map.getZoom(), 9),
        bearing: brg,
        pitch: flat ? 0 : 64,
        offset: mobile ? [0, (container.current?.clientHeight ?? 800) * 0.2] : [-60, 150],
        duration: reduced.current ? 0 : 1700,
        essential: true,
      });
    },
    [byKey, items, topYears, flat, origin],
  );

  // Open a project that arrived in the URL once the map is ready.
  const opened = useRef(false);
  useEffect(() => {
    if (!ready || opened.current) return;
    opened.current = true;
    if (selected) window.setTimeout(() => select(selected), 400);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  const toggleFlat = (next: boolean) => {
    setFlat(next);
    const ms = reduced.current ? 0 : 1000;
    layerRef.current?.setHeight(next ? 0 : 1, ms);
    mapRef.current?.easeTo({ pitch: next ? 0 : selected ? 64 : 56, duration: ms });
  };

  useEffect(() => {
    const el = container.current;
    const map = mapRef.current;
    if (!ready || !el || !map) return;
    let raf = 0;
    const onMove = (e: MouseEvent) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const key = layerRef.current?.pick(e.clientX - r.left, e.clientY - r.top) ?? null;
        setHover(key);
        map.getCanvas().style.cursor = key ? "pointer" : "";
      });
    };
    const onLeave = () => setHover(null);
    const onClick = (e: { point: { x: number; y: number } }) => {
      const key = layerRef.current?.pick(e.point.x, e.point.y) ?? null;
      if (key) select(key);
      else if (selected) setSelected(null);
    };
    el.addEventListener("mousemove", onMove);
    el.addEventListener("mouseleave", onLeave);
    map.on("click", onClick);
    return () => {
      cancelAnimationFrame(raf);
      el.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseleave", onLeave);
      map.off("click", onClick);
    };
  }, [ready, select, selected]);

  // --- playback: the plane climbs the window, rippling each documented in-service date ----------------------------
  const stop = useCallback(() => {
    if (playRef.current) cancelAnimationFrame(playRef.current);
    playRef.current = null;
    rippleRef.current = false;
    setPlaying(false);
  }, []);
  const play = useCallback(() => {
    if (reduced.current) {
      setPlaneDay(hi);
      return;
    }
    stop();
    const ms = Math.min(Math.max((range[1] - range[0] + 1) * 450, 4000), 12000);
    const t0 = performance.now();
    rippleRef.current = false;
    setPlaneDay(lo);
    setPlaying(true);
    const tick = (now: number) => {
      const t = Math.min((now - t0) / ms, 1);
      rippleRef.current = true;
      setPlaneDay(lo + (hi - lo) * t);
      if (t < 1) playRef.current = requestAnimationFrame(tick);
      else {
        playRef.current = null;
        rippleRef.current = false;
        setPlaying(false);
      }
    };
    playRef.current = requestAnimationFrame(tick);
  }, [lo, hi, range, stop]);
  useEffect(() => () => {
    if (playRef.current) cancelAnimationFrame(playRef.current);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target instanceof HTMLInputElement || target instanceof HTMLSelectElement || !!target?.closest?.(".maplibregl-map");
      const list = origin?.center && near.length ? near : rows;
      if (!typing && (e.key === "ArrowDown" || e.key === "ArrowUp") && list.length) {
        e.preventDefault();
        const i = list.findIndex((r) => r.p.key === selected);
        const next = e.key === "ArrowDown" ? (i + 1) % list.length : (i <= 0 ? list.length : i) - 1;
        select(list[next].p.key);
      }
      if (e.key === "Escape") {
        stop();
        setSelected(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [rows, near, origin, selected, select, stop]);

  const onRange = useCallback(
    (f: number, t: number) => {
      stop();
      setRange([f, t]);
      fit((yearStart(t + 1) - yearStart(f)) / YEAR_D);
      setPlaneDay((d) => Math.min(Math.max(d, yearStart(f)), yearStart(t + 1)));
    },
    [stop, fit],
  );
  const onPlane = useCallback((fy: number) => setPlaneDay(dayOfFrac(fy)), []);
  const onScrubStart = useCallback(() => {
    if (playRef.current) stop();
    rippleRef.current = true;
  }, [stop]);
  const onPreview = useCallback((k: string | null) => {
    setHover(null);
    setPreview(k);
  }, []);

  const origin404 = originKey && !origin ? "That origin project isn't in the current datasets." : origin && !origin.center ? "The origin project has no located center, so nothing can be measured from it." : null;

  // --- render -----------------------------------------------------------------------------------------------------
  return (
    <main className={s.stage} data-national-dataset={national.dataset ?? undefined}>
      <div
        ref={container}
        className={s.map}
        role="region"
        aria-label={`History: ${rows.length} located projects with documented events between ${range[0]} and ${range[1]}, stacked at their dates above a map. The list and ledger carry the same facts.`}
      />
      <div className={s.vignette} aria-hidden />
      <div className={s.grain} aria-hidden />

      <p className="visually-hidden" role="status" aria-live="polite">
        {project ? `Selected: ${project.name}. ${project.events.length} documented events.${project.thread ? ` ${project.thread.text}.` : ""}` : ""}
      </p>
      <div className={s.labels} aria-hidden hidden={!!failure}>
        {labelSpecs.map((l) => (
          <div
            key={l.id}
            className={`${s.label} ${s[`l_${l.kind}`] ?? ""}`}
            ref={(el) => {
              if (el) labelEls.current.set(l.id, el);
              else labelEls.current.delete(l.id);
            }}
          >
            <div className={s.labelInner}>{l.text}</div>
          </div>
        ))}
        {sel?.thread && selItem?.thread && !flat ? (
          <div
            className={s.bracket}
            data-late={sel.thread.days > 0 ? "1" : "0"}
            ref={(el) => {
              if (el) labelEls.current.set("bracket", el);
              else labelEls.current.delete("bracket");
            }}
          >
            <span>
              <b>{signed(sel.thread.days)}</b> days
            </span>
          </div>
        ) : null}
      </div>

      <div className={s.left}>
        <header className={s.masthead}>
          <p className={s.overline}>GridBridge · History · the record</p>
          <h1 className={s.title}>
            What was built, <em>when</em>.
          </h1>
          <p className={s.lede}>
            Every located project stands where it is; each documented date sits at its height. Move the amber plane
            through the years and watch the record fill in.
          </p>
          <dl className={s.stats}>
            <div>
              <dt>Projects</dt>
              <dd>{rows.length.toLocaleString("en-US")}</dd>
            </div>
            <div>
              <dt>Events</dt>
              <dd>{eventCount.toLocaleString("en-US")}</dd>
            </div>
            <div>
              <dt>Built</dt>
              <dd>{builtRows.length.toLocaleString("en-US")}</dd>
            </div>
          </dl>
          {required.length ? (
            <p className={s.verdict}>
              <b>{early}</b> of {required.length} upgrades documenting both a required date and an actual in-service date entered
              service before the required date.
            </p>
          ) : null}
          <p className={s.provenance}>
            Window <b>{range[0]}–{range[1]}</b> · analysis date <b>{fmtDay(analysisDay)}</b>
            <br />
            {national.available ? (
              <>
                National dataset <code>{national.dataset}</code>
                {national.mode === "snapshot" ? " (committed snapshot)" : ""}
                {national.truncated ? " · map limit reached" : ""}
              </>
            ) : (
              <>National records unavailable{national.reason ? ` (${national.reason})` : ""}.</>
            )}
            {!data.legacyAvailable ? " · Legacy filings unavailable." : ""}
          </p>
          <p className={s.nullNote}>
            <span aria-hidden /> No contract or award evidence in this dataset. That is not evidence no contract existed.
          </p>
          <button type="button" className={s.play} onClick={() => (playing ? stop() : play())} disabled={!ready || !rows.length}>
            <span aria-hidden>{playing ? "■" : "▶"}</span> {playing ? "Stop" : "Play the record"}
          </button>
          {data.fixtureMode ? <p className={s.fixture}>Sample legacy data · fixture mode</p> : null}
        </header>

        <nav className={s.panel} aria-label="Projects with documented history">
          <div className={s.tabs} role="group" aria-label="Which events">
            {MEANINGS.map(({ v, label, help }) => (
              <button key={v} type="button" aria-pressed={show === v} title={help} onClick={() => setShow(v)}>
                {label}
              </button>
            ))}
          </div>
          <div className={s.filters}>
            <input type="search" placeholder="Search name, ID or owner" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search projects" />
            <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
              <option value="">All sources</option>
              {sources.map(([id, title]) => (
                <option key={id} value={id}>
                  {title}
                </option>
              ))}
            </select>
          </div>
          <div className={s.listScroll}>
            {origin404 ? <p className={s.warnNote}>{origin404}</p> : null}
            {origin?.center ? (
              <section className={s.origin} aria-label="Near the origin project">
                <header>
                  <span>Near this project · {NEAR_MI} mi</span>
                  <button type="button" onClick={() => setOriginKey(null)}>
                    Clear
                  </button>
                </header>
                <p>
                  <i style={{ background: color(origin) }} /> <b>{origin.name}</b>
                </p>
                <p className={s.aid}>
                  {near.length} located project{near.length === 1 ? "" : "s"} with documented events in the window. Straight-line miles between stored
                  centers: a research aid, not an overlap, ranking or contractor match.
                </p>
                <ProjectList rows={near} selected={selected} onSelect={select} onPreview={onPreview} />
              </section>
            ) : null}
            <h2 className={s.listHead}>
              {origin?.center ? "Everywhere" : "In the window"} <span>{rows.length}</span>
            </h2>
            {rows.length ? (
              <ProjectList rows={rows} selected={selected} onSelect={select} onPreview={onPreview} />
            ) : (
              <p className={s.empty}>No documented events match. Zero is a result, not a failure to look.</p>
            )}
            {undated.length ? (
              <>
                <h2 className={s.listHead}>
                  Located, no dated event <span>{undated.length}</span>
                </h2>
                <ul className={s.plain}>
                  {undated.map((p) => (
                    <li key={p.key}>
                      <i style={{ background: color(p) }} />
                      {p.name} <em className="unknown">date unknown</em>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {unlocated.length ? (
              <>
                <h2 className={s.listHead}>
                  Legacy, not located <span>{unlocated.length}</span>
                </h2>
                <ul className={s.plain}>
                  {unlocated.map((p) => (
                    <li key={p.key}>
                      <i style={{ background: color(p) }} />
                      {p.name} <em className="unknown">no located endpoint</em>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
            {national.available && national.unlocated ? (
              <p className={s.footnote}>
                {national.unlocated.toLocaleString("en-US")} national records have no located position and are not drawn.{" "}
                <Link href="/explore">Search them in the explorer →</Link>
              </p>
            ) : null}
          </div>
        </nav>
      </div>

      {project ? (
        <aside className={s.detail} aria-label="Selected project" key={project.key} style={{ ["--c" as string]: color(project) }}>
          <button type="button" className={s.close} onClick={() => setSelected(null)} aria-label="Close project">
            ×
          </button>
          <section className={s.proj}>
            <p className={s.projOwner}>{project.owner ?? "Owner unknown"}</p>
            <h2>{project.name}</h2>
            <p className={s.projMeta}>
              {project.source_title ?? project.source_id}
              {project.status ? <> · publisher status “{project.status}”</> : null}
            </p>
            {project.location ? <p className={s.projMeta}>{project.location}</p> : null}
          </section>
          {project.thread ? (
            <div className={s.figure} data-late={project.thread.days > 0 ? "1" : "0"}>
              <strong>{signed(project.thread.days)}</strong>
              <span>{project.thread.text}. Two documented dates; not a construction duration.</span>
            </div>
          ) : null}
          <EventTrack p={project} />
          <ol className={s.events}>
            {project.events.map((e) => (
              <li key={e.id} data-in={intersects(e, lo, hi) ? "1" : "0"}>
                <EventGlyph e={e} />
                <div>
                  <p className={s.evHead}>
                    <b>{e.label}</b>
                    <span data-m={e.meaning}>{MEANING_WORD[e.meaning]}</span>
                  </p>
                  <p className={s.evWhen}>{when(e)}</p>
                  <p className={s.evDesc}>{e.description}</p>
                  <p className={s.evSrc}>
                    {e.source.publisher}
                    {e.source.locator ? <> · <code>{e.source.locator}</code></> : null}
                    {" · retrieved "}
                    {e.source.retrieved_at ? e.source.retrieved_at.slice(0, 10) : <em className="unknown">unknown</em>}
                    {e.source.url ? (
                      <>
                        {" · "}
                        <a href={e.source.url} target="_blank" rel="noreferrer">
                          Source ↗
                        </a>
                      </>
                    ) : null}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          {origin?.center && project.center && origin.key !== project.key ? (
            <p className={s.aid}>{milesBetween(origin.center, project.center).toFixed(1)} mi from {origin.name}, straight line between stored centers.</p>
          ) : null}
          <p className={s.nullNote}>
            <span aria-hidden /> Contractor, award and contract value: none in this dataset.
          </p>
          <p className={s.detailFoot}>
            <code>{project.key}</code>
            {project.identity === "national" ? <Link href={`/explore?text=${encodeURIComponent(project.name.slice(0, 100))}`}>Open in the explorer →</Link> : null}
          </p>
        </aside>
      ) : null}

      <section className={s.dock} aria-label="Legend and controls">
        <ul className={s.legend}>
          <li>
            <i className={s.glyph} data-m="actual" /> Actual in-service date, documented
          </li>
          <li>
            <i className={s.glyph} data-m="plan" /> Plan date: projected, required, revised, filed
          </li>
          <li>
            <i className={s.glyph} data-m="other" /> Other documented event
          </li>
          <li>
            <i className={s.gThread} /> Plan → actual, two documented dates
          </li>
          <li>
            <i className={s.gPlane} /> Year plane · above it, ghosted
          </li>
          <li className={s.utils}>
            <span>
              <i style={{ background: COLOR.national }} /> National, confirmed
            </span>
            <span>
              <i style={{ background: CANDIDATE_COLOR }} /> National, candidate location
            </span>
            <span>
              <i style={{ background: COLOR.DESC }} /> Dominion SC
            </span>
            <span>
              <i style={{ background: COLOR.GPC }} /> Georgia Power
            </span>
          </li>
        </ul>
        <div className={s.controls}>
          <div className={s.seg} role="group" aria-label="Dimensions">
            <button type="button" aria-pressed={flat} onClick={() => toggleFlat(true)}>
              2D
            </button>
            <button type="button" aria-pressed={!flat} onClick={() => toggleFlat(false)}>
              3D
            </button>
          </div>
          <label className={s.slider}>
            <span>
              1 year = <b>{yearPx}px</b>
            </span>
            <input type="range" min={4} max={60} step={1} value={yearPx} disabled={flat} onChange={(e) => setYearPx(Number(e.target.value))} />
          </label>
          <button type="button" className={s.reset} onClick={overview}>
            Overview
          </button>
        </div>
        <p className={s.hint}>Drag to pan · right-drag or ⌃-drag to tilt · ↑ ↓ step through projects · Esc clears</p>
      </section>

      <Ledger
        years={ledger}
        from={range[0]}
        to={range[1]}
        plane={fracYear(planeDay)}
        planeLabel={monthLabel(planeDay)}
        onRange={onRange}
        onPlane={onPlane}
        onScrubStart={onScrubStart}
      />

      <div className={s.counter} data-on={playing ? "1" : "0"} aria-hidden>
        <b>{new Date(planeDay * DAY_MS).getUTCFullYear()}</b>
        <span>
          <b>{builtByPlane.toLocaleString("en-US")}</b> documented in-service dates by then
        </span>
      </div>

      {!ready && !failure ? (
        <div className={s.loading} role="status">
          <svg viewBox="0 0 48 32" aria-hidden>
            <circle cx="18" cy="16" r="12" />
            <circle cx="30" cy="16" r="12" />
          </svg>
          Opening the record…
        </div>
      ) : null}
      {failure ? (
        <div className={s.failure} role="status">
          {failure}
        </div>
      ) : null}
    </main>
  );
}
