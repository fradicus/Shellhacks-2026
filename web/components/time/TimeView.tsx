"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap } from "maplibre-gl";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { InService, Utility, View } from "@/lib/types";
import type { Emphasis, LabelSpec, Projected, TimeItem, TimeLayer } from "./timeLayer";
import { DAYS_PER_YEAR, dayOf, epochYear, fmtDays, span, type Span } from "./timeScale";
import s from "./time.module.css";

export interface TimeProject {
  key: string;
  name: string;
  utility: Utility;
  center: { lat: number; lon: number } | null;
  in_service: InService;
  confidence: "high" | "medium" | "low" | null;
  source_id: string;
  page: number | null;
}
export interface TimePair {
  id: string;
  a: string;
  b: string;
  distance_mi: number;
  time_gap_days: number | null;
  band: 0 | 1;
  view: View;
  rank: number | null;
  review_state: "needs_review" | "confirmed" | "rejected" | null;
}

const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
const COLOR: Record<Utility, string> = { DESC: "#5cc8ff", GPC: "#ffae42", unknown: "#8b93a7" };
const UTILITY: Record<Utility, string> = { DESC: "Dominion Energy SC", GPC: "Georgia Power", unknown: "Owner unknown" };
const VIEWS: { v: View; label: string; help: string }[] = [
  { v: "future", label: "Future", help: "Both dates exact and on or after the analysis date" },
  { v: "historical", label: "Historical", help: "At least one in-service date before the analysis date" },
  { v: "tentative", label: "Tentative", help: "A low-confidence location or a date that isn't exact" },
];
const REVIEW: Record<string, string> = {
  needs_review: "Needs review",
  confirmed: "Confirmed by audit",
  rejected: "Not confirmed by audit",
};
const miles = (d: number) => `${d.toFixed(2)} mi`;
const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** Geographic bearing A -> B in degrees, for turning the camera side-on to a pair. */
function bearing(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180;
  const y = Math.sin((b.lon - a.lon) * r) * Math.cos(b.lat * r);
  const x = Math.cos(a.lat * r) * Math.sin(b.lat * r) - Math.sin(a.lat * r) * Math.cos(b.lat * r) * Math.cos((b.lon - a.lon) * r);
  return (Math.atan2(y, x) * 180) / Math.PI;
}

/** Camera padding that keeps the data clear of the panels: left column on desktop, bottom sheet on phones. */
function overviewPadding(el: HTMLElement | null) {
  const w = el?.clientWidth ?? 1400;
  const h = el?.clientHeight ?? 800;
  return w <= 860
    ? { top: 70, bottom: Math.round(h * 0.5), left: 12, right: 96 }
    : { top: 60, bottom: 150, left: Math.min(460, w * 0.34), right: 250 };
}

function describe(sp: Span, raw: string | null): string {
  if (sp.kind === "exact") return fmtDate(sp.iso);
  if (sp.kind === "range") return `sometime in ${sp.label} (${sp.precision} only)`;
  return raw ? `not exact: “${raw}”` : "no date filed";
}

export function TimeView({
  projects,
  pairs,
  analysisDate,
  fixtureMode,
}: {
  projects: TimeProject[];
  pairs: TimePair[];
  analysisDate: string;
  fixtureMode: boolean;
}) {
  const counts = useMemo(
    () => Object.fromEntries(VIEWS.map(({ v }) => [v, pairs.filter((p) => p.view === v).length])) as Record<View, number>,
    [pairs],
  );
  const [view, setView] = useState<View>(() => VIEWS.find(({ v }) => counts[v] > 0)?.v ?? "future");
  const [pairId, setPairId] = useState<string | null>(null);
  const [projectKey, setProjectKey] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [flat, setFlat] = useState(false);
  const [yearPx, setYearPx] = useState(30);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [trayOpen, setTrayOpen] = useState(false);
  const [tour, setTour] = useState<number | null>(null);
  const tourTimer = useRef<number | null>(null);

  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const layerRef = useRef<TimeLayer | null>(null);
  const labelEls = useRef(new Map<string, HTMLElement>());
  const reduced = useRef(false);
  const leftRef = useRef<HTMLDivElement>(null);
  const detailRef = useRef<HTMLElement>(null);
  const fitPx = useRef(30);
  const incoming = useRef<string | null | undefined>(undefined);
  const selectPairRef = useRef<(id: string | null) => void>(() => {});

  // --- facts, derived once --------------------------------------------------------------------------------------------
  const byKey = useMemo(() => new Map(projects.map((p) => [p.key, p])), [projects]);
  const located = useMemo(() => projects.filter((p) => p.center), [projects]);
  const epoch = useMemo(() => epochYear(located.map((p) => p.in_service)), [located]);
  const spans = useMemo(() => new Map(located.map((p) => [p.key, span(p.in_service, epoch)])), [located, epoch]);
  const todayYears = dayOf(analysisDate, epoch) / DAYS_PER_YEAR;
  const hasRanges = [...spans.values()].some((sp) => sp.kind === "range");
  const undated = located.filter((p) => spans.get(p.key)?.kind === "unknown");
  const notLocated = projects.length - located.length;
  const items: TimeItem[] = useMemo(
    () =>
      located.map((p) => ({ key: p.key, color: COLOR[p.utility], lng: p.center!.lon, lat: p.center!.lat, span: spans.get(p.key)! })),
    [located, spans],
  );
  const topYears = useMemo(() => {
    const tops = [...spans.values()].map((sp) => (sp.kind === "exact" ? sp.day : sp.kind === "range" ? sp.to : 0));
    return Math.max(todayYears, ...tops.map((d) => d / DAYS_PER_YEAR), 1);
  }, [spans, todayYears]);
  const bbox = useMemo(() => {
    const lons = located.map((p) => p.center!.lon);
    const lats = located.map((p) => p.center!.lat);
    return lons.length
      ? ([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)] as const)
      : ([-85.6, 30.3, -78.5, 35.3] as const);
  }, [located]);

  const visible = useMemo(
    () => pairs.filter((p) => p.view === view).sort((x, y) => (x.rank ?? 1e9) - (y.rank ?? 1e9) || x.id.localeCompare(y.id)),
    [pairs, view],
  );
  const pair = pairId ? (pairs.find((p) => p.id === pairId) ?? null) : null;
  const pa = pair ? byKey.get(pair.a) : undefined;
  const pb = pair ? byKey.get(pair.b) : undefined;
  const project = projectKey ? byKey.get(projectKey) : undefined;

  // --- the map, created once ------------------------------------------------------------------------------------------
  useEffect(() => {
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const h = container.current?.clientHeight ?? 800;
    fitPx.current = Math.max(16, Math.min(96, Math.round((h * 0.36) / Math.max(topYears, 1) / 2) * 2));
    setYearPx(fitPx.current);
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const [ml, { createTimeLayer }] = await Promise.all([import("maplibre-gl"), import("./timeLayer")]);
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
          attributionControl: { compact: true },
          maxPitch: 78,
          canvasContextAttributes: { antialias: true },
        });
        mapRef.current = map;
        map.on("error", (e) => {
          if (/fetch|load|tile|style|NetworkError|Failed/i.test(e.error?.message ?? ""))
            setFailure("Basemap tiles failed to load. The time axis and the pair list still work.");
        });
        map.on("load", () => {
          if (!map) return;
          map.setProjection({ type: "mercator" });
          // Quieter basemap: the data is the subject. Points of interest off, labels dimmed.
          for (const l of map.getStyle().layers ?? []) {
            if (l.type === "symbol") {
              if (/poi|transit|aeroway|housenum|road_shield|highway-shield/i.test(l.id)) map.setLayoutProperty(l.id, "visibility", "none");
              else map.setPaintProperty(l.id, "text-opacity", 0.55);
            }
          }
          const layer = createTimeLayer(ml, {
            yearPx,
            onFrame: (pos: Projected) => {
              for (const [id, p] of pos) {
                const el = labelEls.current.get(id);
                if (!el) continue;
                el.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
                el.dataset.on = p.on ? "1" : "0";
              }
              const beads = [...pos].filter(([id]) => id.startsWith("sel-"));
              if (beads.length === 2) {
                const [l, r] = beads[0][1].x <= beads[1][1].x ? beads : [beads[1], beads[0]];
                // Far apart on screen: centred over each bead. Close: pushed to opposite sides so they can't collide.
                const near = Math.abs(r[1].x - l[1].x) < 280;
                labelEls.current.get(l[0])?.setAttribute("data-side", near ? "l" : "c");
                labelEls.current.get(r[0])?.setAttribute("data-side", near ? "r" : "c");
              }
              // Keep bead and hover labels in the open band between the side panels.
              const box = container.current?.getBoundingClientRect();
              if (!box) return;
              const lo = leftRef.current && box.width > 860 ? leftRef.current.getBoundingClientRect().right - box.left + 10 : 8;
              const hi = detailRef.current ? detailRef.current.getBoundingClientRect().left - box.left - 10 : box.width - 8;
              for (const [id, p] of pos) {
                if (!id.startsWith("sel-") && id !== "hover") continue;
                const el = labelEls.current.get(id);
                const inner = el?.firstElementChild as HTMLElement | null;
                if (!el || !inner) continue;
                const w = inner.offsetWidth;
                const side = el.dataset.side ?? (id === "hover" ? "r" : "c");
                const x0 = side === "l" ? p.x - w - 14 : side === "r" ? p.x + 14 : p.x - w / 2;
                const dx = x0 < lo ? lo - x0 : x0 + w > hi ? Math.max(hi - (x0 + w), lo - x0) : 0;
                inner.style.translate = `${dx.toFixed(1)}px 0`;
              }
            },
          });
          layerRef.current = layer;
          if (process.env.NODE_ENV !== "production") (window as unknown as { __tv: unknown }).__tv = { map, layer };
          map.addLayer(layer.layer);
          setReady(true);
        });
      } catch (err) {
        setFailure(`3D view unavailable (${err instanceof Error ? err.message : "WebGL failed"}). The pair list still works.`);
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

  // Data in, then the opening move: top-down, the time axis grows, the camera tilts to show it.
  useEffect(() => {
    const layer = layerRef.current;
    const map = mapRef.current;
    if (!ready || !layer || !map) return;
    layer.setItems(items, todayYears);
    const ms = reduced.current ? 0 : 2200;
    layer.setHeight(1, ms);
    const want = incoming.current ?? new URLSearchParams(window.location.search).get("pair");
    const wanted = pairs.find((p) => p.id === want);
    incoming.current = null;
    if (!wanted) {
      map.easeTo({ pitch: 58, bearing: -16, duration: ms, easing: (t) => 1 - (1 - t) ** 3 });
      return;
    }
    const id = window.setTimeout(() => {
      setView(wanted.view);
      selectPairRef.current(wanted.id);
    }, ms * 0.4);
    return () => window.clearTimeout(id);
    // Runs once per dataset; the pair link is read only on arrival.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, items, todayYears]);

  // --- focus: what's selected, hovered and linked ---------------------------------------------------------------------
  const related = useMemo(() => {
    if (!projectKey) return new Set<string>();
    return new Set(visible.filter((p) => p.a === projectKey || p.b === projectKey).flatMap((p) => [p.a, p.b]));
  }, [visible, projectKey]);

  const emphasis = useCallback(
    (key: string): Emphasis => {
      if (pair) return key === pair.a || key === pair.b ? "sel" : key === hover ? "hot" : "dim";
      if (projectKey) return key === projectKey ? "sel" : related.has(key) || key === hover ? "hot" : "dim";
      return key === hover ? "hot" : "normal";
    },
    [pair, projectKey, related, hover],
  );

  // The ruler stands east of the data (over open water) in the overview; for a pair it stands at the pair's midpoint,
  // so the dimension line is read against the year ticks.
  const rulerAt = useMemo(() => {
    if (pa?.center && pb?.center) return { lng: (pa.center.lon + pb.center.lon) / 2, lat: (pa.center.lat + pb.center.lat) / 2 };
    return { lng: bbox[2] + 0.35, lat: bbox[1] + (bbox[3] - bbox[1]) * 0.42 };
  }, [pa, pb, bbox]);

  const dimension = pair && pair.time_gap_days !== null && spans.get(pair.a)?.kind === "exact" && spans.get(pair.b)?.kind === "exact";

  useEffect(() => {
    const layer = layerRef.current;
    if (!ready || !layer) return;
    layer.setFocus({
      emphasis,
      links: visible
        .filter((p) => !(pairId || projectKey) || p.id === pairId || p.a === projectKey || p.b === projectKey)
        .map((p) => ({
        a: p.a,
        b: p.b,
        hot: p.id === pairId || (!!projectKey && (p.a === projectKey || p.b === projectKey)) || (!!hover && (p.a === hover || p.b === hover)),
      })),
      dimension: dimension && pair ? { a: pair.a, b: pair.b } : null,
      ruler: rulerAt,
    });
  }, [ready, emphasis, visible, pairId, projectKey, hover, dimension, pair, rulerAt]);

  useEffect(() => {
    layerRef.current?.setYearPx(yearPx);
  }, [yearPx, ready]);

  // --- labels: React owns their content, the layer moves them every frame ---------------------------------------------
  const heightOf = (key: string) => {
    const sp = spans.get(key);
    return sp?.kind === "exact" ? sp.day / DAYS_PER_YEAR : sp?.kind === "range" ? sp.to / DAYS_PER_YEAR : 0;
  };
  const labelSpecs: (LabelSpec & { text: React.ReactNode; kind: string })[] = [];
  if (!flat) {
    for (let y = 0; y <= Math.ceil(topYears); y++)
      labelSpecs.push({ id: `y${y}`, ...rulerAt, years: y, kind: "tick", text: epoch + y });
    labelSpecs.push({
      id: "today",
      ...rulerAt,
      years: todayYears,
      kind: pair ? "todayShort" : "today",
      text: pair ? "Today" : <>Today · {fmtDate(analysisDate)}</>,
    });
  }
  if (pair && pa?.center && pb?.center) {
    const mid = { lng: (pa.center.lon + pb.center.lon) / 2, lat: (pa.center.lat + pb.center.lat) / 2 };
    labelSpecs.push({ id: "dist", ...mid, years: 0, kind: "dist", text: <>{miles(pair.distance_mi)} apart</> });
    if (dimension && !flat)
      labelSpecs.push({
        id: "gap",
        ...mid,
        years: (heightOf(pair.a) + heightOf(pair.b)) / 2,
        kind: "gap",
        text: fmtDays(pair.time_gap_days!),
      });
    for (const p of [pa, pb])
      labelSpecs.push({ id: `sel-${p.key}`, lng: p.center!.lon, lat: p.center!.lat, years: flat ? 0 : heightOf(p.key), kind: "bead", text: p.name });
  }
  const hovered = hover ? byKey.get(hover) : undefined;
  if (hovered?.center && hover !== pair?.a && hover !== pair?.b)
    labelSpecs.push({
      id: "hover",
      lng: hovered.center.lon,
      lat: hovered.center.lat,
      years: flat ? 0 : heightOf(hovered.key),
      kind: "hover",
      text: (
        <>
          <b>{hovered.name}</b>
          <span>
            {UTILITY[hovered.utility]} · {describe(spans.get(hovered.key)!, hovered.in_service.raw)}
          </span>
        </>
      ),
    });
  const labelKey = labelSpecs.map((l) => `${l.id}:${l.lng.toFixed(4)}:${l.lat.toFixed(4)}:${l.years.toFixed(4)}`).join("|");
  useEffect(() => {
    layerRef.current?.setLabels(labelSpecs);
    // labelKey captures every field the layer reads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [labelKey, ready]);

  // --- camera moves ---------------------------------------------------------------------------------------------------
  const frame = useCallback(
    (a: TimeProject | undefined, b: TimeProject | undefined) => {
      const map = mapRef.current;
      if (!map || !a?.center || !b?.center) return;
      const brg = bearing(a.center, b.center) - 90;
      const cam = map.cameraForBounds(
        [
          [Math.min(a.center.lon, b.center.lon), Math.min(a.center.lat, b.center.lat)],
          [Math.max(a.center.lon, b.center.lon), Math.max(a.center.lat, b.center.lat)],
        ],
        {
          padding:
            (container.current?.clientWidth ?? 1400) <= 860
              ? { top: 260, bottom: Math.round((container.current?.clientHeight ?? 800) * 0.5), left: 40, right: 40 }
              : { top: 300, bottom: 150, left: 500, right: 460 },
          bearing: brg,
          maxZoom: 10.5,
        },
      );
      if (!cam) return;
      map.flyTo({ ...cam, bearing: brg, pitch: flat ? 0 : 66, duration: reduced.current ? 0 : 1900, essential: true });
    },
    [flat],
  );

  const selectPair = useCallback(
    (id: string | null) => {
      setPairId(id);
      setProjectKey(null);
      const p = id ? pairs.find((x) => x.id === id) : null;
      if (p) {
        const tops = [p.a, p.b].map((k) => {
          const sp = spans.get(k);
          return sp?.kind === "exact" ? sp.day : sp?.kind === "range" ? sp.to : 0;
        });
        const years = Math.max(...tops, 1) / DAYS_PER_YEAR;
        const room = (container.current?.clientHeight ?? 800) * 0.42;
        setYearPx(Math.max(16, Math.min(84, Math.round(room / years / 2) * 2)));
        frame(byKey.get(p.a), byKey.get(p.b));
      }
    },
    [pairs, byKey, frame, spans],
  );

  useEffect(() => {
    selectPairRef.current = selectPair;
  }, [selectPair]);

  const overview = useCallback(() => {
    setYearPx(fitPx.current);
    setPairId(null);
    setProjectKey(null);
    const map = mapRef.current;
    if (!map) return;
    const cam = map.cameraForBounds(
      [
        [bbox[0], bbox[1]],
        [bbox[2], bbox[3]],
      ],
      { padding: overviewPadding(container.current), bearing: -16 },
    );
    if (cam) map.flyTo({ ...cam, pitch: flat ? 0 : 58, bearing: -16, duration: reduced.current ? 0 : 1600 });
  }, [bbox, flat]);

  const toggleFlat = (next: boolean) => {
    setFlat(next);
    const ms = reduced.current ? 0 : 1100;
    layerRef.current?.setHeight(next ? 0 : 1, ms);
    mapRef.current?.easeTo({ pitch: next ? 0 : pair ? 66 : 58, duration: ms });
  };

  // Pointer: hover and click on pillars and beads, picked in screen space.
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
      if (!key) {
        if (pairId || projectKey) {
          setPairId(null);
          setProjectKey(null);
        }
        return;
      }
      const best = visible.find((p) => p.a === key || p.b === key);
      if (best) selectPair(best.id);
      else {
        setPairId(null);
        setProjectKey(key);
      }
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
  }, [ready, visible, selectPair, pairId, projectKey]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target instanceof HTMLInputElement || !!target?.closest?.(".maplibregl-map");
      if (!typing && (e.key === "ArrowDown" || e.key === "ArrowUp") && visible.length) {
        e.preventDefault();
        const i = visible.findIndex((p) => p.id === pairId);
        const next = e.key === "ArrowDown" ? (i + 1) % visible.length : (i <= 0 ? visible.length : i) - 1;
        if (tourTimer.current) window.clearTimeout(tourTimer.current);
        setTour(null);
        selectPair(visible[next].id);
        return;
      }
      if (e.key === "Escape") {
        if (tourTimer.current) window.clearTimeout(tourTimer.current);
        setTour(null);
        setPairId(null);
        setProjectKey(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, pairId, selectPair]);

  // The selected pair lives in the URL, so a demo can open straight onto it and a link can be shared.
  useEffect(() => {
    // Hold an incoming ?pair= until the intro has opened it; syncing earlier would erase it.
    if (incoming.current === undefined) incoming.current = new URLSearchParams(window.location.search).get("pair");
    if (!pairId && incoming.current) return;
    const u = new URL(window.location.href);
    if (pairId) u.searchParams.set("pair", pairId);
    else u.searchParams.delete("pair");
    window.history.replaceState(window.history.state, "", u);
  }, [pairId]);

  // --- the story: a short guided flight for people who have never read a transmission filing ---------------------------
  // Every caption is built from stored facts: the top-ranked pair, then the pair with the widest day gap.
  const story = useMemo(() => {
    const first = visible[0];
    const wide = [...visible]
      .filter((p) => p.id !== first?.id && p.time_gap_days !== null)
      .sort((x, y) => y.time_gap_days! - x.time_gap_days!)[0];
    const name = (k: string) => byKey.get(k)?.name ?? k;
    const facts = (p: TimePair) =>
      `${miles(p.distance_mi)} apart on the ground, ${p.time_gap_days === null ? "day gap unknown" : fmtDays(p.time_gap_days) + " apart in service"}.`;
    const names = (p: TimePair) => `${name(p.a)}  ·  ${name(p.b)}`;
    const steps: { pair: string | null; kicker: string; text: string; names?: string }[] = [
      {
        pair: null,
        kicker: "The map",
        text: `${located.length} utility projects from public filings, each raised to its filed in-service date. The glass sheet is today.`,
      },
    ];
    if (first)
      steps.push({ pair: first.id, kicker: "The top lead", text: `${facts(first)} The first call to make.`, names: names(first) });
    if (wide && first)
      steps.push({
        pair: wide.id,
        kicker: wide.distance_mi < first.distance_mi ? "Closer, but not sooner" : "Near, but not together",
        text: `${facts(wide)} Same neighbourhood, different years, so it ranks lower.`,
        names: names(wide),
      });
    steps.push({ pair: null, kicker: "The rule", text: "Geography decides an overlap. Time only ranks it. Every number here is traced to a filing page." });
    return steps;
  }, [visible, byKey, located.length]);

  const stopTour = useCallback(() => {
    if (tourTimer.current) window.clearTimeout(tourTimer.current);
    tourTimer.current = null;
    setTour(null);
  }, []);
  const stepRef = useRef<(i: number) => void>(() => {});
  const goStep = useCallback(
    (i: number) => {
      const step = story[i];
      if (tourTimer.current) window.clearTimeout(tourTimer.current);
      if (!step) {
        tourTimer.current = null;
        setTour(null);
        return;
      }
      setTour(i);
      if (step.pair) selectPair(step.pair);
      else overview();
      tourTimer.current = window.setTimeout(() => stepRef.current(i + 1), 7000);
    },
    [story, selectPair, overview],
  );
  useEffect(() => {
    stepRef.current = goStep;
  }, [goStep]);
  useEffect(() => () => {
    if (tourTimer.current) window.clearTimeout(tourTimer.current);
  }, []);

  const changeView = (v: View) => {
    setView(v);
    setPairId(null);
    setProjectKey(null);
  };

  // --- render ---------------------------------------------------------------------------------------------------------
  return (
    <main className={s.stage}>
      <div
        ref={container}
        className={s.map}
        role="region"
        aria-label={`Time view: ${located.length} located projects raised to their in-service dates above a map. The pair list carries the same facts.`}
      />
      <div className={s.vignette} aria-hidden />
      <div className={s.grain} aria-hidden />

      <div className={s.labels} aria-hidden>
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
      </div>

      <div className={s.left} ref={leftRef}>
      <header className={s.masthead}>
        <p className={s.overline}>GridBridge · Time view</p>
        <h1 className={s.title}>
          When, <em>above</em> where.
        </h1>
        <p className={s.lede}>
          Every located project rises to its filed in-service date. Distance on the ground decides an overlap; height only
          shows timing.
        </p>
        <dl className={s.stats}>
          <div>
            <dt>Drawn</dt>
            <dd>{located.length}</dd>
          </div>
          <div>
            <dt>Not located</dt>
            <dd>{notLocated}</dd>
          </div>
          <div>
            <dt>Ground</dt>
            <dd>1 Jan {epoch}</dd>
          </div>
        </dl>
        <button type="button" className={s.play} onClick={() => (tour === null ? goStep(0) : stopTour())} disabled={!ready}>
          <span aria-hidden>{tour === null ? "▶" : "■"}</span> {tour === null ? "Play the story" : "Stop the story"}
        </button>
        {fixtureMode ? <p className={s.fixture}>Sample data · fixture mode</p> : null}
      </header>

      <nav className={s.pairs} aria-label="Overlap pairs">
        <div className={s.tabs} role="group" aria-label="Which pairs">
          {VIEWS.map(({ v, label, help }) => (
            <button key={v} type="button" aria-pressed={view === v} title={help} onClick={() => changeView(v)}>
              {label} <span>{counts[v]}</span>
            </button>
          ))}
        </div>
        {visible.length ? (
          <ol className={s.pairList}>
            {visible.map((p, i) => {
              const a = byKey.get(p.a);
              const b = byKey.get(p.b);
              return (
                <li key={p.id}>
                  <button
                    type="button"
                    aria-pressed={p.id === pairId}
                    title={`${p.a} · ${p.b}`}
                    onClick={() => {
                      stopTour();
                      selectPair(p.id === pairId ? null : p.id);
                    }}
                    onMouseEnter={() => setHover(null)}
                  >
                    <span className={s.rank}>{String(i + 1).padStart(2, "0")}</span>
                    <span className={s.pairNames}>
                      <span>
                        <i style={{ background: COLOR[a?.utility ?? "unknown"] }} />
                        {a?.name ?? p.a}
                      </span>
                      <span>
                        <i style={{ background: COLOR[b?.utility ?? "unknown"] }} />
                        {b?.name ?? p.b}
                      </span>
                    </span>
                    <span className={s.pairNums}>
                      <span>{miles(p.distance_mi)}</span>
                      <span>{p.time_gap_days === null ? "gap —" : `${p.time_gap_days.toLocaleString("en-US")} d`}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        ) : (
          <p className={s.empty}>No {view} pairs in this data. Zero is a valid result.</p>
        )}
        <p className={s.footnote}>Priority order as stored: nearer band first, then the smaller exact day gap.</p>
      </nav>
      <section className={s.tray} aria-label="What is not drawn">
        <button type="button" onClick={() => setTrayOpen((o) => !o)} aria-expanded={trayOpen}>
          <span>Not drawn</span>
          <b>{notLocated}</b> without a located endpoint · <b>{undated.length}</b> located without an exact date
        </button>
        {trayOpen ? (
          <div className={s.trayBody}>
            <p>
              A project needs at least one located endpoint to stand on the map. {notLocated} current projects have none yet,
              so they are listed on the overlap page but not drawn here.
            </p>
            {undated.length ? (
              <>
                <p>Located, but the filing gives no single date. They sit on the ground with no height:</p>
                <ul>
                  {undated.map((p) => (
                    <li key={p.key}>
                      <b>{p.name}</b> · “{p.in_service.raw ?? "no date"}”
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </div>
        ) : null}
      </section>
      </div>


      {pair && pa && pb ? (
        <aside className={s.detail} aria-label="Selected pair" key={pair.id} ref={detailRef}>
          <button type="button" className={s.close} onClick={() => selectPair(null)} aria-label="Close pair">
            ×
          </button>
          <div className={s.figures}>
            <div>
              <strong>{pair.distance_mi.toFixed(2)}</strong>
              <span>miles apart, centre to centre</span>
            </div>
            <div>
              <strong>{pair.time_gap_days === null ? "—" : pair.time_gap_days.toLocaleString("en-US")}</strong>
              <span>{pair.time_gap_days === null ? "day gap unknown: a date isn't exact" : "days between in-service dates"}</span>
            </div>
          </div>
          {[pa, pb].map((p) => (
            <section key={p.key} className={s.proj} style={{ ["--c" as string]: COLOR[p.utility] }}>
              <p className={s.projUtil}>{UTILITY[p.utility]}</p>
              <h2>{p.name}</h2>
              <p>
                In service {describe(spans.get(p.key) ?? { kind: "unknown" }, p.in_service.raw)}
                {p.in_service.raw ? <span className={s.raw}> · filed “{p.in_service.raw}”</span> : null}
              </p>
              <p className={s.src}>
                {p.source_id}
                {p.page !== null ? ` p. ${p.page}` : ""} · location {p.confidence ?? "unknown"} confidence
              </p>
            </section>
          ))}
          <div className={s.detailFoot}>
            <span className={s.review} data-state={pair.review_state ?? "needs_review"}>
              {REVIEW[pair.review_state ?? "needs_review"]}
            </span>
            <Link href={`/pair/${encodeURIComponent(pair.id)}`} className={s.evidence}>
              Evidence &amp; coordination card →
            </Link>
          </div>
        </aside>
      ) : project ? (
        <aside className={s.detail} aria-label="Selected project" key={project.key} ref={detailRef}>
          <button type="button" className={s.close} onClick={() => setProjectKey(null)} aria-label="Close project">
            ×
          </button>
          <section className={s.proj} style={{ ["--c" as string]: COLOR[project.utility] }}>
            <p className={s.projUtil}>{UTILITY[project.utility]}</p>
            <h2>{project.name}</h2>
            <p>In service {describe(spans.get(project.key) ?? { kind: "unknown" }, project.in_service.raw)}</p>
            <p className={s.src}>
              {project.source_id}
              {project.page !== null ? ` p. ${project.page}` : ""} · location {project.confidence ?? "unknown"} confidence
            </p>
          </section>
          <p className={s.note}>
            {related.size ? `In ${related.size - 1} ${view} pair${related.size === 2 ? "" : "s"}; linked projects glow.` : `Not in any ${view} pair.`}
          </p>
        </aside>
      ) : null}

      <section className={s.dock} aria-label="Legend and controls">
        <ul className={s.legend}>
          <li>
            <i className={s.gBead} /> Exact in-service date
          </li>
          {hasRanges ? (
            <li>
              <i className={s.gColumn} /> Only a month or year filed: the whole span, no day picked
            </li>
          ) : null}
          <li>
            <i className={s.gSheet} /> Today, {fmtDate(analysisDate)} · 10-mile grid
          </li>
          <li>
            <i className={s.gDim} /> Day gap of the selected pair
          </li>
          <li className={s.utils}>
            <span>
              <i style={{ background: COLOR.DESC }} /> Dominion SC
            </span>
            <span>
              <i style={{ background: COLOR.GPC }} /> Georgia Power
            </span>
            <span>
              <i style={{ background: COLOR.unknown }} /> Owner unknown
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
            <input
              type="range"
              min={16}
              max={96}
              step={2}
              value={yearPx}
              disabled={flat}
              onChange={(e) => setYearPx(Number(e.target.value))}
            />
          </label>
          <button type="button" className={s.reset} onClick={overview}>
            Overview
          </button>
        </div>
        <p className={s.hint}>Drag to pan · right-drag or ⌃-drag to tilt · ↑ ↓ step through pairs · Esc clears</p>
      </section>


      {tour !== null && story[tour] ? (
        <div className={s.caption} role="status" aria-live="polite" key={tour}>
          <p className={s.kicker}>
            {String(tour + 1).padStart(2, "0")} / {String(story.length).padStart(2, "0")} · {story[tour].kicker}
          </p>
          <p className={s.captionText}>{story[tour].text}</p>
          {story[tour].names ? <p className={s.captionNames}>{story[tour].names}</p> : null}
          <div className={s.progress} aria-hidden>
            {story.map((_, i) => (
              <i key={i} data-state={i < tour ? "done" : i === tour ? "now" : "next"} />
            ))}
          </div>
        </div>
      ) : null}
      {!ready && !failure ? <div className={s.loading}>Raising the time axis…</div> : null}
      {failure ? (
        <div className={s.failure} role="status">
          {failure}
        </div>
      ) : null}
    </main>
  );
}
