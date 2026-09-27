"use client";

import { useCandidatePairs } from "./useCandidatePairs";
import { nationalTimeProjects } from "./nationalProjects";
import { bearing } from "./sceneCamera";
import { SceneControls } from "./SceneControls";
import { ScopeBar, type ScopeOption } from "./ScopeBar";
import { INKS, NO_STATE_INK } from "./stateInk";
import { formatScope, haversineMi, inScope, parseScope, planName, planOf, RULE_MI, scopeName, statesOf, type Scope, type ScopeGeography } from "./scope";

import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap } from "maplibre-gl";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { NationalProjectSummary, NationalExplorerPayload } from "@/lib/national/types";
import type { NationalTier } from "./nationalProjects";
import { NationalProjectEvidence } from "./NationalProjectEvidence";
import type { InService, Utility, View } from "@/lib/types";
import type { Emphasis, LabelSpec, Projected, SweepState, TimeItem, TimeLayer } from "./timeLayer";
import { DAYS_PER_YEAR, dayOf, epochYear, fmtDays, span, type Span } from "./timeScale";
import s from "./time.module.css";

export interface TimeProject {
  key: string;
  name: string;
  utility: Utility;
  owner_code: string | null;
  center: { lat: number; lon: number } | null;
  in_service: InService;
  confidence: "high" | "medium" | "low" | null;
  source_id: string;
  page: number | null;
  national?: { project: NationalProjectSummary; tier: NationalTier };
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
  candidate?: boolean;
  review_state: "needs_review" | "confirmed" | "rejected" | null;
}

const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
const UTILITY: Record<Utility, string> = { DESC: "Dominion Energy SC", GPC: "Georgia Power", unknown: "Owner not mapped" };
/** An unmapped owner still has a filed code (MEAG, GTC ...); say which, and that it isn't matched to a utility. */
const owner = (p: TimeProject) =>
  p.national ? (p.national.project.owner ?? "Owner unknown") : p.utility === "unknown" && p.owner_code ? `Owner code ${p.owner_code}, not mapped` : UTILITY[p.utility];
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
/** F37: History opens around this project's stored center, as a research aid. */
const pastWork = (key: string) => `/history?origin=${encodeURIComponent(key)}`;
const SWEEP_MS = 4200;
const BOOTH_IDLE_MS = 25_000;
/** 25 statute miles in degrees of latitude (1° ≈ 69.05 mi), to place the rule's label on its circle. */
const RULE_DEG_LAT = 25 / 69.05;
/** A chosen date on the axis (years after 1 Jan of the epoch year) as "Mar 2029". Display only. */
const monthOf = (epoch: number, years: number) =>
  new Date(Date.UTC(epoch, 0, 1) + years * DAYS_PER_YEAR * 86_400_000).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** Camera padding that keeps the data clear of the panels: left column on desktop, bottom sheet on phones. */
function overviewPadding(el: HTMLElement | null) {
  const w = el?.clientWidth ?? 1400;
  const h = el?.clientHeight ?? 800;
  return w <= 860
    ? { top: 70, bottom: Math.round(h * 0.5), left: 12, right: 96 }
    : { top: 60, bottom: 150, left: Math.min(460, w * 0.34), right: 420 };
}

/** Drawing only: a date before the axis ground lies on the ground; a span crossing it starts at the ground. */
function clampToGround(sp: Span): Span {
  if (sp.kind === "exact") return sp.day < 0 ? { kind: "unknown" } : sp;
  if (sp.kind === "range") return sp.to <= 0 ? { kind: "unknown" } : sp.from < 0 ? { ...sp, from: 0 } : sp;
  return sp;
}

function describe(sp: Span, raw: string | null): string {
  if (sp.kind === "exact") return fmtDate(sp.iso);
  if (sp.kind === "range") return `sometime in ${sp.label} (${sp.precision} only)`;
  return raw ? `not exact: “${raw}”` : "no date filed";
}

export function TimeView({
  projects: baseProjects,
  pairs: legacyPairs,
  initialScope,
  initialPairId,
  analysisDate,
  fixtureMode,
  national,
  geography,
  stateInk,
  legacyAvailable,
  pairsAvailable,
}: {
  initialScope: string | null;
  initialPairId: string | null;
  projects: TimeProject[];
  pairs: TimePair[];
  analysisDate: string;
  fixtureMode: boolean;
  legacyAvailable: boolean;
  pairsAvailable: boolean;
  geography: ScopeGeography;
  /** State FIPS → pen color; a project is drawn in its first stored state's ink. */
  stateInk: Record<string, string>;
  national: { available: boolean; mode: NationalExplorerPayload["mode"]; dataset: string | null;
    drawn: number; inService: number; unlocated: number; truncated: boolean };
}) {
  const [view, setView] = useState<View>(() => VIEWS.find(({ v }) => legacyPairs.some((p) => p.view === v))?.v ?? "future");
  const [scope, setScope] = useState<Scope | null>(() => parseScope(initialScope));
  const [candidateMode, setCandidateMode] = useState(!initialPairId || initialPairId.startsWith("npc:"));
  const [sharedId, setSharedId] = useState(initialPairId?.startsWith("npc:") ? initialPairId : null);
  const candidates = useCandidatePairs(national.dataset, scope ? formatScope(scope) : null, candidateMode, sharedId);
  const candidatePairs = useMemo<TimePair[]>(() => (candidates.page?.pairs ?? []).map((p) => ({ ...p,
    candidate: true, view: "tentative", review_state: null })), [candidates.page]);
  const pairs = useMemo<TimePair[]>(() => candidateMode ? [...candidatePairs,
    ...(candidates.shared?.pairs ?? []).filter((p) => !candidatePairs.some((x) => x.id === p.id)).map((p): TimePair =>
      ({ ...p, candidate: true, view: "tentative", review_state: null }))] : legacyPairs,
    [candidateMode, candidatePairs, candidates.shared, legacyPairs]);
  const projects = useMemo(() => {
    const known = new Set(baseProjects.map((p) => p.key));
    const extra = [...new Map([...(candidates.page?.projects ?? []), ...(candidates.shared?.projects ?? [])]
      .filter((p) => !known.has(p._id)).map((p) => [p._id, p])).values()];
    return extra.length ? [...baseProjects, ...nationalTimeProjects(extra)] : baseProjects;
  }, [baseProjects, candidates.page, candidates.shared]);
  const [pinArmed, setPinArmed] = useState(false);
  const [pairId, setPairId] = useState<string | null>(null);
  const [projectKey, setProjectKey] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  // A pair under the pointer (or keyboard focus) in the list: previewed on the map before any click.
  const [preview, setPreview] = useState<string | null>(null);
  const [flat, setFlat] = useState(false);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [trayOpen, setTrayOpen] = useState(false);
  const [projectQuery, setProjectQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [tour, setTour] = useState<number | null>(null);
  const [asOf, setAsOf] = useState<number | null>(null);
  const [booth, setBooth] = useState(false);
  const boothRef = useRef(false);
  const sweepEl = useRef<HTMLDivElement>(null);
  const tourTimer = useRef<number | null>(null);

  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const layerRef = useRef<TimeLayer | null>(null);
  const labelEls = useRef(new Map<string, HTMLElement>());
  const reduced = useRef(false);
  const leftRef = useRef<HTMLDivElement>(null);
  const detailRef = useRef<HTMLElement>(null);
  const epochRef = useRef(0);
  const topYearsRef = useRef(1);
  const incoming = useRef<string | null | undefined>(undefined);
  const selectPairRef = useRef<(id: string | null) => void>(() => {});
  const stopTourRef = useRef<() => void>(() => {});
  const scopeRead = useRef(false);

  // --- facts, derived once --------------------------------------------------------------------------------------------
  const projectColor = useCallback((p: TimeProject) => stateInk[statesOf(p)[0]] ?? NO_STATE_INK, [stateInk]);
  const byKey = useMemo(() => new Map(projects.map((p) => [p.key, p])), [projects]);
  const located = useMemo(() => projects.filter((p) => p.center), [projects]);
  // --- scope: which part of the map is lifted (spec 15–21) ------------------------------------------------------------
  const regionOf = useMemo(() => new Map(geography.states.map((st) => [st.fips, st.region])), [geography]);
  const scoped = useMemo(() => (scope ? located.filter((p) => inScope(p, scope, regionOf)) : located), [scope, located, regionOf]);
  const scopeKeys = useMemo(() => (scope ? new Set(scoped.map((p) => p.key)) : null), [scope, scoped]);
  const scopeLabel = scope ? scopeName(scope, geography) : null;
  const scopeOptions = useMemo(() => {
    const tally = (keyOf: (p: TimeProject) => string[]) => {
      const n = new Map<string, number>();
      for (const p of located) for (const k of new Set(keyOf(p))) n.set(k, (n.get(k) ?? 0) + 1);
      return n;
    };
    const byCount = (a: ScopeOption, b: ScopeOption) => b.count - a.count || a.label.localeCompare(b.label);
    const regions = tally((p) => statesOf(p).map((st) => regionOf.get(st) ?? "").filter(Boolean));
    const plans = tally((p) => { const pl = planOf(p); return pl ? [pl] : []; });
    const states = tally(statesOf);
    // Places read as a map legend: the country, its regions by size, then states A–Z (people look a state up by name).
    return [
      { tab: "places", group: null, scope: null, label: "United States", count: located.length },
      ...geography.regions.filter((r) => regions.get(r.code)).map((r): ScopeOption =>
        ({ tab: "places", group: "Regions", scope: { kind: "region", code: r.code }, label: r.name, count: regions.get(r.code)! })).sort(byCount),
      ...geography.states.filter((st) => states.get(st.fips)).map((st): ScopeOption =>
        ({ tab: "places", group: "States", scope: { kind: "state", code: st.fips }, label: st.name, hint: st.usps, count: states.get(st.fips)! }))
        .sort((a, b) => a.label.localeCompare(b.label)),
      ...[...plans].map(([code, count]): ScopeOption =>
        ({ tab: "grid", group: "Grid plans", scope: { kind: "plan", code }, label: planName(code), count })).sort(byCount),
    ] satisfies ScopeOption[];
  }, [located, geography, regionOf]);
  const unplanned = useMemo(() => located.filter((p) => !planOf(p)).length, [located]);
  // The planning window: the ground is 1 Jan of the year before the analysis date (or the earliest drawn year, if
  // later), so one old filing can't stretch the axis. Earlier dates keep their facts and lie flat on the ground.
  const analysisYear = Number(analysisDate.slice(0, 4));
  const epoch = useMemo(() => Math.max(Math.min(epochYear(located.map((p) => p.in_service)), analysisYear), analysisYear - 1), [located, analysisYear]);
  const spans = useMemo(() => new Map(located.map((p) => [p.key, span(p.in_service, epoch)])), [located, epoch]);
  const drawn = useMemo(() => new Map([...spans].map(([k, sp]) => [k, clampToGround(sp)])), [spans]);
  const beforeGround = located.filter((p) => spans.get(p.key)?.kind !== "unknown" && drawn.get(p.key)?.kind === "unknown").length;
  const todayYears = dayOf(analysisDate, epoch) / DAYS_PER_YEAR;
  const hasRanges = [...spans.values()].some((sp) => sp.kind === "range");
  const undated = located.filter((p) => spans.get(p.key)?.kind === "unknown");
  const sources = useMemo(() => [...new Set(projects.map((p) => p.source_id))].sort(), [projects]);
  // The drawer lists every current project: the drawn ones and the ones that can't be placed yet.
  const listed = useMemo(() => {
    const q = projectQuery.trim().toLowerCase();
    const hit = (p: TimeProject) => !q || p.name.toLowerCase().includes(q) || p.key.toLowerCase().includes(q);
    const byName = (a: TimeProject, b: TimeProject) => a.name.localeCompare(b.name);
    const pin = scope?.kind === "pin" ? scope : null;
    const near = (p: TimeProject) => (pin ? haversineMi(pin.lat, pin.lon, p.center!.lat, p.center!.lon) : 0);
    return {
      drawn: scoped.filter(hit).sort((a, b) => near(a) - near(b) || byName(a, b)),
      unplaced: scope ? [] : projects.filter((p) => !p.center && hit(p)).sort(byName),
      near: pin ? near : null,
    };
  }, [projects, scoped, scope, projectQuery]);
  const notLocated = projects.length - located.length;
  const items: TimeItem[] = useMemo(
    () =>
      located.map((p) => ({ key: p.key, color: projectColor(p), lng: p.center!.lon, lat: p.center!.lat, span: drawn.get(p.key)!,
        outline: p.national?.tier === "tentative", ringed: p.national?.tier === "confirmed" })),
    [located, drawn, projectColor],
  );
  const tierCounts = useMemo(() => {
    const counts: Record<NationalTier, number> = { confirmed: 0, official: 0, tentative: 0 };
    for (const p of projects) if (p.national) counts[p.national.tier]++;
    return counts;
  }, [projects]);
  const topYears = useMemo(() => {
    const tops = [...drawn.values()].map((sp) => (sp.kind === "exact" ? sp.day : sp.kind === "range" ? sp.to : 0));
    return Math.max(todayYears, ...tops.map((d) => d / DAYS_PER_YEAR), 1);
  }, [drawn, todayYears]);
  useEffect(() => {
    epochRef.current = epoch;
    topYearsRef.current = topYears;
  }, [epoch, topYears]);
  // The scope's frame: its drawn projects, or the pin's 25-mile circle.
  const scopeBox = useMemo(() => {
    if (scope?.kind === "pin") {
      const dLat = RULE_MI / 69.05;
      const dLon = dLat / Math.cos((scope.lat * Math.PI) / 180);
      return [scope.lon - dLon, scope.lat - dLat, scope.lon + dLon, scope.lat + dLat] as const;
    }
    if (!scoped.length || !scope) return null;
    const lons = scoped.map((p) => p.center!.lon);
    const lats = scoped.map((p) => p.center!.lat);
    return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)] as const;
  }, [scope, scoped]);
  const bbox = useMemo(() => {
    const lons = located.map((p) => p.center!.lon);
    const lats = located.map((p) => p.center!.lat);
    return lons.length
      ? ([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)] as const)
      : ([-85.6, 30.3, -78.5, 35.3] as const);
  }, [located]);

  // Pairs follow the scope: both ends inside it.
  const scopedPairs = useMemo(() => (scopeKeys ? pairs.filter((p) => scopeKeys.has(p.a) && scopeKeys.has(p.b)) : pairs), [pairs, scopeKeys]);
  const counts = useMemo(
    () => Object.fromEntries(VIEWS.map(({ v }) => [v, scopedPairs.filter((p) => p.view === v).length])) as Record<View, number>,
    [scopedPairs],
  );
  const visible = useMemo(
    () => candidateMode ? candidatePairs : scopedPairs.filter((p) => p.view === view).sort((x, y) => (x.rank ?? 1e9) - (y.rank ?? 1e9) || x.id.localeCompare(y.id)),
    [scopedPairs, view, candidateMode, candidatePairs],
  );
  const pair = pairId ? (pairs.find((p) => p.id === pairId) ?? null) : null;
  const previewed = !pair && preview ? (pairs.find((p) => p.id === preview) ?? null) : null;
  const pa = pair ? byKey.get(pair.a) : undefined;
  const pb = pair ? byKey.get(pair.b) : undefined;
  const project = projectKey ? byKey.get(projectKey) : undefined;

  // --- the map, created once ------------------------------------------------------------------------------------------
  useEffect(() => {
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
            onSweep: (st: SweepState) => {
              const el = sweepEl.current;
              if (!el) return;
              el.dataset.on = st ? "1" : "0";
              if (!st) return;
              const [year, count] = el.querySelectorAll("b");
              year.textContent = String(epochRef.current + Math.min(Math.floor(st.years), Math.ceil(topYearsRef.current)));
              count.textContent = `${st.shown} of ${st.total}`;
            },
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
          // An incoming ?scope= (malformed values are ignored) arrives with the data.
          scopeRead.current = true;
          const incomingScope = parseScope(new URLSearchParams(window.location.search).get("scope"));
          if (incomingScope) setScope(incomingScope);
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        setFailure(
          /webgl/i.test(msg) || !msg
            ? "3D view unavailable: this browser has no WebGL2. The pair list, pair details and All projects still work."
            : `3D view unavailable (${msg.slice(0, 120)}). The pair list still works.`,
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
    if (!want?.startsWith("npc:")) incoming.current = null;
    if (!wanted) {
      // The timelapse: pillars rise in the order they were filed to enter service, while the camera tilts.
      layer.sweepIn(reduced.current ? 0 : SWEEP_MS, 700);
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
      const lit = key === pair?.a || key === pair?.b || key === previewed?.a || key === previewed?.b || key === projectKey || key === hover;
      if (scopeKeys && !scopeKeys.has(key) && !lit) return "out";
      if (pair) return key === pair.a || key === pair.b ? "sel" : key === hover ? "hot" : "dim";
      if (previewed) return key === previewed.a || key === previewed.b ? "hot" : "dim";
      if (projectKey) return key === projectKey ? "sel" : related.has(key) || key === hover ? "hot" : "dim";
      return key === hover ? "hot" : "normal";
    },
    [pair, previewed, projectKey, related, hover, scopeKeys],
  );

  // The ruler stands east of the data (over open water) in the overview; for a pair it stands at the pair's midpoint,
  // so the dimension line is read against the year ticks.
  const rulerAt = useMemo(() => {
    if (pa?.center && pb?.center) return { lng: (pa.center.lon + pb.center.lon) / 2, lat: (pa.center.lat + pb.center.lat) / 2 };
    const b = scopeBox ?? bbox;
    return { lng: b[2] + (scopeBox ? (b[2] - b[0]) * 0.04 + 0.03 : 0.35), lat: b[1] + (b[3] - b[1]) * 0.42 };
  }, [pa, pb, bbox, scopeBox]);

  const dimension = pair && pair.time_gap_days !== null && drawn.get(pair.a)?.kind === "exact" && drawn.get(pair.b)?.kind === "exact";

  useEffect(() => {
    const layer = layerRef.current;
    if (!ready || !layer) return;
    layer.setFocus({
      emphasis,
      links: (candidateMode ? [pair ?? previewed].filter((p): p is TimePair => !!p) : visible)
        .filter((p) => !(pairId || projectKey) || p.id === pairId || p.a === projectKey || p.b === projectKey)
        .map((p) => ({
        a: p.a,
        b: p.b,
        hot:
          p.id === pairId ||
          p.id === previewed?.id ||
          (!!projectKey && (p.a === projectKey || p.b === projectKey)) ||
          (!!hover && (p.a === hover || p.b === hover)),
      })),
      dimension: dimension && pair ? { a: pair.a, b: pair.b } : null,
      ruler: rulerAt,
    });
  }, [ready, emphasis, visible, pairId, projectKey, hover, previewed, dimension, pair, rulerAt, candidateMode]);

  // Pillar height follows the zoom (yearPxAt); a selected pair's own top sets the cap so its day gap fills the room.
  useEffect(() => {
    const top = (k: string) => {
      const sp = drawn.get(k);
      return sp?.kind === "exact" ? sp.day : sp?.kind === "range" ? sp.to : 0;
    };
    layerRef.current?.setFitYears(pair ? Math.max(top(pair.a), top(pair.b)) / DAYS_PER_YEAR : null);
  }, [pair, drawn, ready]);

  // The 25-mile rule, drawn around both stored centers of the selected (or previewed) pair.
  const ra = pa ?? (previewed ? byKey.get(previewed.a) : undefined);
  const rb = pb ?? (previewed ? byKey.get(previewed.b) : undefined);
  const pin = scope?.kind === "pin" ? scope : null;
  useEffect(() => {
    if (!ready) return;
    layerRef.current?.setRules(
      ra?.center && rb?.center
        ? {
            a: { lng: ra.center.lon, lat: ra.center.lat, color: projectColor(ra) },
            b: { lng: rb.center.lon, lat: rb.center.lat, color: projectColor(rb) },
          }
        : pin
          ? { a: { lng: pin.lon, lat: pin.lat, color: "#bfe9ff" } }
          : null,
    );
  }, [ready, ra, rb, pin, projectColor]);

  useEffect(() => {
    layerRef.current?.setAsOf(asOf);
  }, [asOf, ready]);

  // --- labels: React owns their content, the layer moves them every frame ---------------------------------------------
  const heightOf = (key: string) => {
    const sp = drawn.get(key);
    return sp?.kind === "exact" ? sp.day / DAYS_PER_YEAR : sp?.kind === "range" ? sp.to / DAYS_PER_YEAR : 0;
  };
  const labelSpecs: (LabelSpec & { text: React.ReactNode; kind: string })[] = [];
  if (!flat) {
    for (let y = 0; y <= Math.ceil(topYears); y++)
      labelSpecs.push({ id: `y${y}`, ...rulerAt, years: y, kind: "tick", text: epoch + y });
    labelSpecs.push({
      id: "today",
      ...rulerAt,
      years: asOf ?? todayYears,
      kind: pair ? "todayShort" : "today",
      text: asOf !== null ? <>As of {monthOf(epoch, asOf)}</> : pair ? "Today" : <>Today · {fmtDate(analysisDate)}</>,
    });
  }
  if (pair && pa?.center && pb?.center) {
    const mid = { lng: (pa.center.lon + pb.center.lon) / 2, lat: (pa.center.lat + pb.center.lat) / 2 };
    labelSpecs.push({ id: "dist", ...mid, years: 0, kind: "dist", text: <>{miles(pair.distance_mi)} apart</> });
    // The rule's label sits where A's 25-mile circle crosses the far side of the view: the camera faces A→B minus 90°.
    const far = ((bearing(pa.center, pb.center) - 90) * Math.PI) / 180;
    labelSpecs.push({
      id: "rule",
      lng: pa.center.lon + (RULE_DEG_LAT * Math.sin(far)) / Math.cos((pa.center.lat * Math.PI) / 180),
      lat: pa.center.lat + RULE_DEG_LAT * Math.cos(far),
      years: 0,
      kind: "rule",
      text: pair.candidate ? "25 mi provisional circle" : "25 mi overlap rule",
    });
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
  if (pin && !(ra && rb)) {
    labelSpecs.push({ id: "pin", lng: pin.lon, lat: pin.lat, years: 0, kind: "pin", text: null });
    labelSpecs.push({
      id: "pinRule",
      lng: pin.lon,
      lat: pin.lat + RULE_DEG_LAT,
      years: 0,
      kind: "rule",
      text: <>{RULE_MI} mi · {scoped.length} project{scoped.length === 1 ? "" : "s"}</>,
    });
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
          <b>
            <i style={{ background: projectColor(hovered) }} />
            {hovered.name}
          </b>
          <span>
            {owner(hovered)} · {describe(spans.get(hovered.key)!, hovered.in_service.raw)}
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
              ? {
                  top: Math.round((container.current?.clientHeight ?? 800) * 0.3) + 60,
                  bottom: Math.round((container.current?.clientHeight ?? 800) * 0.5),
                  left: 40,
                  right: 40,
                }
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
      if (p) frame(byKey.get(p.a), byKey.get(p.b));
    },
    [pairs, byKey, frame],
  );

  useEffect(() => {
    selectPairRef.current = selectPair;
  }, [selectPair]);
  const openedShared = useRef<string | null>(null);
  useEffect(() => {
    if (!ready || !sharedId || !candidates.shared || openedShared.current === sharedId) return;
    openedShared.current = sharedId;
    incoming.current = null;
    selectPairRef.current(sharedId);
  }, [ready, sharedId, candidates.shared]);

  const overview = useCallback(() => {
    setPairId(null);
    setProjectKey(null);
    setScope(null);
    setPinArmed(false);
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

  // Arrival (spec 18): fly to the scope and let it rise in date order. Clearing is handled by Overview.
  const scopeId = scope ? formatScope(scope) : null;
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !scopeBox) return;
    const cam = map.cameraForBounds(
      [
        [scopeBox[0], scopeBox[1]],
        [scopeBox[2], scopeBox[3]],
      ],
      { padding: overviewPadding(container.current), bearing: -16, maxZoom: 9.5 },
    );
    if (cam) map.flyTo({ ...cam, pitch: flat ? 0 : 58, bearing: -16, duration: reduced.current ? 0 : 1600, essential: true });
    layerRef.current?.sweepIn(reduced.current ? 0 : 1600, 250);
    // Only a new scope moves the camera; flat and the box follow from it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopeId, ready]);

  // The scope lives in the URL too (spec 21). The map's load reads it once; until then the URL is left alone.
  useEffect(() => {
    if (!scopeRead.current) return;
    const u = new URL(window.location.href);
    if (scopeId) u.searchParams.set("scope", scopeId);
    else u.searchParams.delete("scope");
    window.history.replaceState(window.history.state, "", u);
  }, [scopeId]);

  const pickScope = useCallback(
    (next: Scope | null) => {
      stopTourRef.current();
      setPinArmed(false);
      setSharedId(null);
      incoming.current = null;
      setPairId(null);
      setPreview(null);
      if (next) setScope(next);
      else overview();
    },
    [overview],
  );

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
        setHover(pinArmed ? null : key);
        map.getCanvas().style.cursor = pinArmed ? "crosshair" : key ? "pointer" : "";
      });
    };
    const onLeave = () => setHover(null);
    const onClick = (e: { point: { x: number; y: number }; lngLat: { lng: number; lat: number } }) => {
      if (pinArmed) {
        pickScope({ kind: "pin", lat: e.lngLat.lat, lon: e.lngLat.lng });
        map.getCanvas().style.cursor = "";
        return;
      }
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
  }, [ready, visible, selectPair, pairId, projectKey, pinArmed, pickScope]);

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
        setTrayOpen(false);
        if (tourTimer.current) window.clearTimeout(tourTimer.current);
        setTour(null);
        // One layer at a time: an armed pin, then the selection, then the scope.
        if (pinArmed) setPinArmed(false);
        else if (pairId || projectKey) {
          setPairId(null);
          setProjectKey(null);
        } else if (scope) pickScope(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, pairId, projectKey, selectPair, pinArmed, scope, pickScope]);

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
    steps.push({ pair: null, kicker: "The rule", text: candidateMode ? "Provisional candidates are under 25 straight-line miles apart. Routes and construction schedules have not been checked." : "Geography decides an overlap. Time only ranks it. Every number here is traced to a filing page." });
    return steps;
  }, [visible, byKey, located.length, candidateMode]);

  const stopTour = useCallback(() => {
    if (tourTimer.current) window.clearTimeout(tourTimer.current);
    tourTimer.current = null;
    setTour(null);
  }, []);
  useEffect(() => {
    stopTourRef.current = stopTour;
  }, [stopTour]);
  const stepRef = useRef<(i: number) => void>(() => {});
  const goStep = useCallback(
    (i: number) => {
      const step = story[i];
      if (tourTimer.current) window.clearTimeout(tourTimer.current);
      if (!step) {
        // Booth mode loops the story; otherwise it ends.
        if (boothRef.current) {
          tourTimer.current = window.setTimeout(() => stepRef.current(0), 1500);
          return;
        }
        tourTimer.current = null;
        setTour(null);
        return;
      }
      setTour(i);
      if (step.pair) selectPair(step.pair);
      else overview();
      if (i === 0) layerRef.current?.sweepIn(reduced.current ? 0 : SWEEP_MS, 900);
      // Booth mode: a slow orbit once the camera has arrived.
      if (boothRef.current && !reduced.current) {
        const map = mapRef.current;
        window.setTimeout(() => {
          if (boothRef.current && map) map.rotateTo(map.getBearing() + 24, { duration: 4600, easing: (t) => t });
        }, 2100);
      }
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

  // Booth mode: idle for a while and the view presents itself; any input hands it back.
  useEffect(() => {
    if (!ready || reduced.current) return;
    let idle = 0;
    const arm = () => {
      window.clearTimeout(idle);
      idle = window.setTimeout(() => {
        boothRef.current = true;
        setBooth(true);
        stepRef.current(0);
      }, BOOTH_IDLE_MS);
    };
    const poke = () => {
      if (boothRef.current) {
        boothRef.current = false;
        setBooth(false);
        stopTour();
        mapRef.current?.stop();
      }
      arm();
    };
    const evs = ["pointerdown", "pointermove", "keydown", "wheel", "touchstart"] as const;
    evs.forEach((e) => window.addEventListener(e, poke, { passive: true }));
    arm();
    return () => {
      window.clearTimeout(idle);
      evs.forEach((e) => window.removeEventListener(e, poke));
    };
  }, [ready, stopTour]);

  const changeView = (v: View) => {
    setView(v);
    setPairId(null);
    setProjectKey(null);
  };

  // --- render ---------------------------------------------------------------------------------------------------------
  return (
    <main className={s.stage} data-national-dataset={national.dataset ?? undefined}>
      <div
        ref={container}
        className={s.map}
        role="region"
        aria-label={`Time view: ${located.length} located projects raised to their in-service dates above a map. The pair list carries the same facts.`}
      />
      <div className={s.vignette} aria-hidden />
      <div className={s.grain} aria-hidden />

      <p className="visually-hidden" role="status" aria-live="polite">
        {pair && pa && pb
          ? `Selected: ${pa.name} and ${pb.name}. ${miles(pair.distance_mi)} apart; ${
              pair.time_gap_days === null ? "day gap unknown" : fmtDays(pair.time_gap_days) + " between in-service dates"
            }. ${pair.candidate ? "Provisional candidate" : REVIEW[pair.review_state ?? "needs_review"]}.`
          : project
            ? `Selected project: ${project.name}.`
            : ""}
      </p>
      {/* Labels ride on the 3D layer; without it they have nowhere to be. */}
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
      </div>

      <ScopeBar current={scopeLabel} count={scoped.length} total={located.length} options={scopeOptions} unplanned={unplanned}
        initialTab={scope?.kind === "plan" ? "grid" : "places"} pinArmed={pinArmed}
        onPick={pickScope} onClear={() => pickScope(null)} onPin={setPinArmed} />

      <div className={s.left} ref={leftRef}>
      <header className={s.masthead}>
        <p className={s.overline}>Common Ground · Overlaps in time</p>
        <h1 className={s.title}>
          When, <em>above</em> where.
        </h1>
        <p className={s.lede}>
          Every located project rises to its filed in-service date. {candidateMode
            ? "Nearby candidates are under 25 straight-line miles apart; height shows filed timing."
            : "Distance on the ground decides an overlap; height only shows timing."}
        </p>
        <details className={s.provenance} open={!candidateMode}>
          <summary>Data and sources · {located.length.toLocaleString("en-US")} mapped projects</summary>
        <dl className={s.stats}>
          <div>
            <dt>Drawn</dt>
            <dd>{located.length}</dd>
          </div>
          <div>
            <dt>Legacy unlocated</dt>
            <dd>{notLocated}</dd>
          </div>
          <div>
            <dt>Ground</dt>
            <dd>1 Jan {epoch}</dd>
          </div>
        </dl>
        <p className={s.provenance}>
          Analysis date <b>{fmtDate(analysisDate)}</b>
        </p>
        <details className={s.provenance}>
          <summary>{sources.length} sources</summary>
          {sources.map((id) => <div key={id}><code>{id}</code></div>)}
        </details>
        {!legacyAvailable ? <p role="status" className={s.provenance}>Legacy projects unavailable; national projects remain available.</p> : null}
        <details className={s.provenance}>
          <summary>National coverage and location confidence</summary>
          <p>{national.available ? <>{national.drawn} national projects not yet in service included ({tierCounts.confirmed} confirmed,
            {" "}{tierCounts.official} owner-published, {tierCounts.tentative} tentative; only confirmed ones are independently reviewed).
            {national.inService ? <> {national.inService} already in service are in <Link href="/history">History →</Link></> : null}
            {national.mode === "snapshot" ? " Committed snapshot mode." : ""}
            {national.truncated ? " National map limit reached; more records are available in the explorer." : ""}
          </> : "National projects unavailable; showing the legacy dataset."}
          {" "}<Link href="/explore">Explore national records{national.available ? ` (${national.unlocated} unlocated)` : ""} →</Link>
          </p>
        </details>
        </details>
        <button type="button" className={s.play} onClick={() => (tour === null ? goStep(0) : stopTour())} disabled={!ready}>
          <span aria-hidden>{tour === null ? "▶" : "■"}</span> {tour === null ? "Play the story" : "Stop the story"}
        </button>
        {fixtureMode ? <p className={s.fixture}>Sample data · fixture mode</p> : null}
      </header>

      <nav className={s.pairs} aria-label="Overlap pairs">
        <div className={s.tabs} role="group" aria-label="Pair collection">
          {[true, false].map((mode) => <button key={String(mode)} type="button" aria-pressed={candidateMode === mode}
            onClick={() => { setCandidateMode(mode); setPairId(null); setPreview(null); setSharedId(null); incoming.current = null; }}>
            {mode ? "Nearby candidates" : "Legacy pairs"}
          </button>)}
        </div>
        {candidateMode ? <p className={s.footnote} aria-live="polite">
          {candidates.page ? `${candidates.page.total.toLocaleString("en-US")} candidates · ${scopeLabel ?? "United States"}` : candidates.loading ? "Loading candidates…" : "Candidates unavailable"}
        </p> : <div className={s.tabs} role="group" aria-label="Which pairs">
          {VIEWS.map(({ v, label, help }) => (
            <button key={v} type="button" aria-pressed={view === v} title={help} onClick={() => changeView(v)}>
              {label} <span>{counts[v]}</span>
            </button>
          ))}
        </div>}
        {candidateMode && candidates.error ? <div className={s.empty} role="alert">
          <p>{candidates.error}</p>
          <button type="button" onClick={() => candidates.refresh ? window.location.reload() : candidates.retry()}>
            {candidates.refresh ? "Refresh page" : "Retry candidates"}
          </button>
        </div> : null}
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
                    onMouseEnter={() => {
                      setHover(null);
                      setPreview(p.id);
                    }}
                    onMouseLeave={() => setPreview(null)}
                    onFocus={() => setPreview(p.id)}
                    onBlur={() => setPreview(null)}
                  >
                    <span className={s.rank}>{String(i + 1).padStart(2, "0")}</span>
                    <span className={`${s.pairNames} ${candidateMode ? s.candidateNames : ""}`}>
                      <span>
                        <i style={{ background: a ? projectColor(a) : NO_STATE_INK }} />
                        {(a?.name ?? p.a).replaceAll("_", " ")}
                      </span>
                      <span>
                        <i style={{ background: b ? projectColor(b) : NO_STATE_INK }} />
                        {(b?.name ?? p.b).replaceAll("_", " ")}
                      </span>
                    </span>
                    <span className={s.pairNums}>
                      <span>{miles(p.distance_mi)}</span>
                      {p.candidate ? <small title="Location evidence tier">{[a, b].some((x) => x?.national?.tier === "tentative") ? "Tentative"
                        : [a, b].some((x) => x?.national?.tier === "official") ? "Published" : "Confirmed"}</small> : null}
                      <span>{p.time_gap_days === null ? "gap —" : `${p.time_gap_days.toLocaleString("en-US")} d`}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        ) : candidateMode && candidates.error ? null : (
          <div className={s.empty}>
            <p>{candidateMode ? (candidates.loading ? "Loading candidates…" : candidates.error ? "" : "No candidates with both projects in this scope.") : !pairsAvailable ? "Legacy overlap pairs unavailable. Project discovery remains available."
              : scopeLabel ? `No ${view} pairs with both projects ${scope?.kind === "pin" ? `within ${RULE_MI} mi of the pin` : `in ${scopeLabel}`}. Zero is a valid result, not a failure to look.`
              : `No ${view} pairs in this data. Zero is a valid result, not a failure to look.`}</p>
            {!candidateMode && VIEWS.filter(({ v }) => v !== view && counts[v] > 0).map(({ v, label }) => (
              <button key={v} type="button" onClick={() => changeView(v)}>
                Show {label.toLowerCase()} ({counts[v]}) →
              </button>
            ))}
          </div>
        )}
        {candidateMode && candidates.page?.nextOffset != null ? <button type="button" className={s.loadMore}
          disabled={candidates.loading} onClick={candidates.loadMore}>{candidates.loading ? "Loading…" : "Load more candidates"}</button> : null}
        <p className={s.footnote}>{candidateMode
          ? "Provisional · under 25 miles straight-line. Driving routes and construction schedules have not been checked."
          : "Priority order as stored: nearer band first, then the smaller exact day gap."}</p>
      </nav>
      <section className={s.tray} aria-label="All projects">
        <button type="button" onClick={() => setTrayOpen((o) => !o)} aria-expanded={trayOpen} aria-controls="all-projects">
          <span>Projects</span>
          {scope ? <><b>{scoped.length}</b> of {located.length} drawn</> : <><b>{located.length}</b> drawn</>} · <b>{notLocated}</b> not located
          {undated.length ? (
            <>
              {" "}
              · <b>{undated.length}</b> no exact date
            </>
          ) : null}
          {beforeGround ? (
            <>
              {" "}
              · <b>{beforeGround}</b> dated before {epoch}, on the ground
            </>
          ) : null}
          <i aria-hidden>{trayOpen ? "×" : "→"}</i>
        </button>
      </section>
      </div>


      {trayOpen ? (
        <aside className={s.drawer} id="all-projects" aria-label="All projects">
          <header className={s.drawerHead}>
            <h2>All projects</h2>
            <button type="button" className={s.close} onClick={() => setTrayOpen(false)} aria-label="Close all projects">
              ×
            </button>
          </header>
          <p className={s.drawerNote}>
            Legacy projects and national map points: confirmed, owner-published or tentative (hollow beads). Unlocated legacy projects are listed below.
            Other national records remain searchable in the national explorer.
          </p>
          <input
            type="search"
            className={s.drawerSearch}
            placeholder="Filter by name or ID"
            value={projectQuery}
            onChange={(e) => setProjectQuery(e.target.value)}
            aria-label="Filter projects by name or ID"
          />
          <div className={s.drawerBody}>
            <h3>
              {scopeLabel ? `Drawn in ${scope?.kind === "pin" ? `${RULE_MI} mi of the pin, nearest first` : scopeLabel}` : "Drawn"} <span>{listed.drawn.length}</span>
            </h3>
            <ul>
              {listed.drawn.map((p) => (
                <li key={p.key}>
                  <button
                    type="button"
                    aria-pressed={p.key === projectKey}
                    onClick={() => {
                      setPairId(null);
                      setProjectKey(p.key);
                      setTrayOpen(false);
                      stopTour();
                      mapRef.current?.easeTo({
                        center: [p.center!.lon, p.center!.lat],
                        zoom: Math.max(mapRef.current.getZoom(), 7.5),
                        duration: reduced.current ? 0 : 900,
                      });
                    }}
                  >
                    <i style={{ background: projectColor(p) }} />
                    <b>{p.name}</b>
                    <span>
                      {listed.near ? `${listed.near(p).toFixed(1)} mi · ` : null}
                      {describe(spans.get(p.key) ?? { kind: "unknown" }, p.in_service.raw)} · <code>{p.key}</code>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {scope ? null : <h3>
              Legacy unlocated <span>{listed.unplaced.length}</span>
            </h3>}
            <ul>
              {listed.unplaced.map((p) => (
                <li key={p.key} className={s.unplaced}>
                  <i style={{ background: projectColor(p) }} />
                  <b>{p.name}</b>
                  <span>
                    {p.in_service.raw ? `filed “${p.in_service.raw}”` : "no date filed"} · <code>{p.key}</code> ·{" "}
                    <em className="unknown">no located endpoint</em>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      ) : null}

      {pair && pa && pb ? (
        <aside className={s.detail} aria-label="Selected pair" key={pair.id} ref={detailRef}>
          <button type="button" className={s.close} onClick={() => selectPair(null)} aria-label="Close pair">
            ×
          </button>
          <div className={s.figures}>
            <div>
              <strong>{pair.distance_mi.toFixed(2)}</strong>
              <span>{pair.candidate ? "straight-line miles between centers" : "miles apart, centre to centre"}</span>
            </div>
            <div>
              <strong>{pair.time_gap_days === null ? "—" : pair.time_gap_days.toLocaleString("en-US")}</strong>
              <span>{pair.time_gap_days === null ? "day gap unknown: a date isn't exact" : "days between in-service dates"}</span>
            </div>
          </div>
          {[pa, pb].map((p) => (
            <section key={p.key} className={s.proj} style={{ ["--c" as string]: projectColor(p) }}>
              <p className={s.projUtil}>{owner(p)}</p>
              <h2>{p.name}</h2>
              <p>
                In service {describe(spans.get(p.key) ?? { kind: "unknown" }, p.in_service.raw)}
                {p.in_service.raw ? <span className={s.raw}> · filed “{p.in_service.raw}”</span> : null}
              </p>
              <p className={s.src}>
                {p.source_id}
                {p.page !== null ? ` p. ${p.page}` : ""}{p.national ? ` · ${p.national.tier} location` : ` · location ${p.confidence ?? "unknown"} confidence`}
              </p>
              {p.national ? <CandidateEvidence project={p.national.project} tier={p.national.tier} dataset={national.dataset} /> : null}
              <Link href={pastWork(p.key)} className={s.evidence}>
                Past work nearby →
              </Link>
            </section>
          ))}
          <div className={s.detailFoot}>
            <span className={s.review} data-state={pair.review_state ?? "needs_review"}>
              {pair.candidate ? "Provisional candidate" : REVIEW[pair.review_state ?? "needs_review"]}
            </span>
            <button
              type="button"
              className={s.copy}
              onClick={() =>
                navigator.clipboard?.writeText(window.location.href).then(() => {
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 1600);
                })
              }
            >
              {copied ? "Copied" : "Copy link"}
            </button>
            {!pair.candidate ? <Link href={`/pair/${encodeURIComponent(pair.id)}`} className={s.evidence}>
              Open evidence →
            </Link> : null}
          </div>
        </aside>
      ) : project ? (
        <aside className={s.detail} aria-label="Selected project" key={project.key} ref={detailRef}>
          <button type="button" className={s.close} onClick={() => setProjectKey(null)} aria-label="Close project">
            ×
          </button>
          <section className={s.proj} style={{ ["--c" as string]: projectColor(project) }}>
            <p className={s.projUtil}>{owner(project)}</p>
            <h2>{project.name}</h2>
            <p>Filed in-service milestone: {describe(spans.get(project.key) ?? { kind: "unknown" }, project.in_service.raw)}</p>
            {!project.national ? <p className={s.src}>
              {project.source_id}
              {project.page !== null ? ` p. ${project.page}` : ""} · location {project.confidence ?? "unknown"} confidence
            </p> : null}
          </section>
          {project.national ? <NationalProjectEvidence {...project.national} dataset={national.dataset} /> : <p className={s.note}>
            {related.size ? `In ${related.size - 1} ${view} pair${related.size === 2 ? "" : "s"}; linked projects glow.` : `Not in any ${view} pair.`}
          </p>}
          <div className={s.projectActions}>
            {project.center ? (
              <button type="button" className={s.evidence} onClick={() => pickScope({ kind: "pin", lat: project.center!.lat, lon: project.center!.lon })}>
                Everything within {RULE_MI} mi →
              </button>
            ) : null}
            <Link href={pastWork(project.key)} className={s.evidence}>
              Find past work nearby in History →
            </Link>
          </div>
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
          {scope ? (
            <li>
              <i className={s.gTrace} /> Outside the scope: grey ground trace, no date shown
            </li>
          ) : null}
          <li className={s.utils}>
            <span>
              <i style={{ background: `conic-gradient(${INKS.join(", ")}, ${INKS[0]})` }} /> Color: the project&apos;s state
            </span>
          </li>
          <li className={s.utils}>
            {tierCounts.confirmed > 0 ? (
              <span title="Location independently reviewed">
                <i style={{ background: NO_STATE_INK, boxShadow: `0 0 0 2px #0b0f16, 0 0 0 3.2px ${NO_STATE_INK}` }} /> Confirmed
              </span>
            ) : null}
            <span title="Located from the owner's own filing or publication, not independently reviewed">
              <i style={{ background: NO_STATE_INK, boxShadow: "none" }} /> Owner-published
            </span>
            {tierCounts.tentative > 0 ? (
              <span title="Location not independently reviewed">
                <i style={{ background: "transparent", boxShadow: `inset 0 0 0 1.5px ${NO_STATE_INK}` }} /> Tentative location
              </span>
            ) : null}
          </li>
        </ul>
        <SceneControls styles={s} flat={flat} onFlat={toggleFlat} onOverview={overview} />
        <label className={s.scrub}>
          <span>
            Sheet at <b>{asOf === null ? `Today · ${fmtDate(analysisDate)}` : monthOf(epoch, asOf)}</b>
            {asOf !== null ? (
              <>
                {" · "}
                {
                  [...spans.values()].filter((sp) => sp.kind !== "unknown" && (sp.kind === "exact" ? sp.day : sp.to) / DAYS_PER_YEAR <= asOf)
                    .length
                }{" "}
                of {[...spans.values()].filter((sp) => sp.kind !== "unknown").length} filed in service by then
              </>
            ) : null}
          </span>
          <span className={s.scrubRow}>
            <input
              type="range"
              min={0}
              max={Math.ceil(topYears)}
              step={1 / 12}
              value={asOf ?? todayYears}
              disabled={flat}
              aria-label="Move the sheet to another date"
              onChange={(e) => {
                const v = Number(e.target.value);
                setAsOf(Math.abs(v - todayYears) < 1 / 24 ? null : v);
              }}
            />
            {asOf !== null ? (
              <button type="button" onClick={() => setAsOf(null)}>
                Today
              </button>
            ) : null}
          </span>
        </label>
        <p className={s.hint}>Drag to pan · right-drag or ⌃-drag to tilt · ↑ ↓ step through pairs · Esc clears</p>
      </section>


      {tour !== null && story[tour] ? (
        <div className={s.caption} role="status" aria-live="polite" key={tour}>
          {booth ? (
            <p className={s.booth}>
              <i aria-hidden /> Presenting · move the mouse to explore
            </p>
          ) : null}
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
      <div className={s.sweep} ref={sweepEl} data-on="0" aria-hidden>
        <b />
        <span>
          <b /> projects filed in service by then
        </span>
      </div>
      {!ready && !failure ? (
        <div className={s.loading} role="status">
          <svg viewBox="0 0 48 32" aria-hidden>
            <circle cx="18" cy="16" r="12" />
            <circle cx="30" cy="16" r="12" />
          </svg>
          Raising the time axis…
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

function CandidateEvidence({ project, tier, dataset }: { project: NationalProjectSummary; tier: NationalTier; dataset: string | null }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={(e) => setOpen(e.currentTarget.open)}>
    <summary>Source evidence · {tier} location</summary>
    {open ? <NationalProjectEvidence project={project} dataset={dataset} /> : null}
  </details>;
}
