"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONSource, Map as MlMap, Popup as MlPopup } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { fmtMiles } from "@/components/ui";
import type { MatchRow, Project } from "@/lib/types";
import s from "./map.module.css";

export type Selection = { kind: "pair"; id: string } | { kind: "project"; key: string } | null;

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const COLORS = { DESC: "#2563eb", GPC: "#ea580c", unknown: "#71717a" };
const SOUTHEAST: [number, number, number, number] = [-85.6, 30.3, -78.5, 35.3];

type LngLat = [number, number];

function lngLat(p: Project | null | undefined): LngLat | null {
  return p?.center ? [p.center.lon, p.center.lat] : null;
}

export function MapView({
  projects,
  matches,
  selection,
  onSelect,
}: {
  projects: Project[];
  matches: MatchRow[];
  selection: Selection;
  onSelect: (s: Selection) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const popupRef = useRef<MlPopup | null>(null);
  const popupCtor = useRef<typeof MlPopup | null>(null);
  const onSelectRef = useRef(onSelect);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  // Which projects and connectors to emphasise for the current selection.
  const { highlighted, links, focus } = useMemo(() => {
    const byKey = new Map(projects.map((p) => [p.project_key, p]));
    let pairs: MatchRow[] = [];
    if (selection?.kind === "pair") pairs = matches.filter((m) => m._id === selection.id);
    if (selection?.kind === "project") pairs = matches.filter((m) => m.a === selection.key || m.b === selection.key);
    const keys = new Set(pairs.flatMap((m) => [m.a, m.b]));
    if (selection?.kind === "project") keys.add(selection.key);
    const segs = pairs
      .map((m) => ({ m, a: lngLat(byKey.get(m.a)), b: lngLat(byKey.get(m.b)) }))
      .filter((x): x is { m: MatchRow; a: LngLat; b: LngLat } => !!x.a && !!x.b);
    const pts = [...keys].map((k) => lngLat(byKey.get(k))).filter((x): x is LngLat => !!x);
    return { highlighted: keys, links: segs, focus: pts };
  }, [projects, matches, selection]);

  // Create the map once.
  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const ml = await import("maplibre-gl");
        if (cancelled || !container.current) return;
        // maplibre v6 locates its module worker relative to its own file, which the bundler moves; load the matching
        // version from jsDelivr instead (maplibre wraps cross-origin worker URLs in a same-origin blob itself).
        ml.setWorkerUrl(`https://cdn.jsdelivr.net/npm/maplibre-gl@${ml.getVersion()}/dist/maplibre-gl-worker.mjs`);
        popupCtor.current = ml.Popup;
        map = new ml.Map({
          container: container.current,
          style: STYLE_URL,
          bounds: SOUTHEAST,
          fitBoundsOptions: { padding: 24 },
          attributionControl: { compact: false },
          cooperativeGestures: false,
        });
        mapRef.current = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.on("error", (e) => {
          const msg = e.error?.message ?? "";
          // Tile/style/glyph fetch failures: keep the map's own layers, tell the user the list still works.
          if (/fetch|load|tile|style|NetworkError|Failed/i.test(msg)) setFailure("Basemap tiles failed to load.");
        });
        map.on("load", () => {
          if (!map) return;
          map.addSource("links", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addSource("projects", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({
            id: "links",
            type: "line",
            source: "links",
            paint: { "line-color": "#1c1c1a", "line-width": 2, "line-dasharray": [2, 2] },
          });
          map.addLayer({
            id: "halo",
            type: "circle",
            source: "projects",
            filter: ["==", ["get", "hl"], 1],
            paint: { "circle-radius": 13, "circle-color": "#facc15", "circle-opacity": 0.55 },
          });
          const color = ["match", ["get", "utility"], "DESC", COLORS.DESC, "GPC", COLORS.GPC, COLORS.unknown];
          map.addLayer({
            id: "projects",
            type: "circle",
            source: "projects",
            paint: {
              "circle-radius": 7,
              // Low-confidence locations draw as hollow rings.
              "circle-color": ["case", ["==", ["get", "conf"], "low"], "rgba(0,0,0,0)", color] as never,
              "circle-stroke-color": ["case", ["==", ["get", "conf"], "low"], color, "#ffffff"] as never,
              "circle-stroke-width": ["case", ["==", ["get", "conf"], "low"], 2.5, 1.5],
            },
          });
          map.on("click", "projects", (e) => {
            const key = e.features?.[0]?.properties?.key;
            if (typeof key === "string") onSelectRef.current({ kind: "project", key });
          });
          map.on("mouseenter", "projects", () => (map!.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", "projects", () => (map!.getCanvas().style.cursor = ""));
          setReady(true);
        });
      } catch (err) {
        // WebGL unavailable or the library failed to load.
        setFailure(`Map unavailable (${err instanceof Error ? err.message : "unknown error"}).`);
      }
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // Push data + selection into the map.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("projects") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: projects
        .filter((p) => p.center)
        .map((p) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [p.center!.lon, p.center!.lat] },
          properties: {
            key: p.project_key,
            name: p.name,
            utility: p.utility,
            conf: p.location_confidence ?? "unknown",
            hl: highlighted.has(p.project_key) ? 1 : 0,
          },
        })),
    });
    (map.getSource("links") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: links.map(({ m, a, b }) => ({
        type: "Feature",
        geometry: { type: "LineString", coordinates: [a, b] },
        properties: { id: m._id },
      })),
    });

    popupRef.current?.remove();
    popupRef.current = null;
    if (links.length === 1 && popupCtor.current) {
      const { m, a, b } = links[0];
      popupRef.current = new popupCtor.current({ closeButton: false, closeOnClick: false, className: s.popup })
        .setLngLat([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
        .setText(`${fmtMiles(m.distance_mi)} center-to-center, not a route`)
        .addTo(map);
    }

    if (focus.length === 1) map.easeTo({ center: focus[0], zoom: Math.max(map.getZoom(), 8) });
    else if (focus.length > 1) {
      const lons = focus.map((p) => p[0]);
      const lats = focus.map((p) => p[1]);
      map.fitBounds(
        [
          [Math.min(...lons), Math.min(...lats)],
          [Math.max(...lons), Math.max(...lats)],
        ],
        { padding: 80, maxZoom: 10 },
      );
    }
  }, [ready, projects, highlighted, links, focus]);

  const located = projects.filter((p) => p.center).length;

  return (
    <div className={s.mapWrap}>
      <div
        ref={container}
        className={s.map}
        role="region"
        aria-label={`Map of ${located} located projects. The overlap list and project table carry the same data.`}
      />
      {!ready && !failure ? <div className={s.mapStatus}>Loading map…</div> : null}
      {failure ? (
        <div className={s.mapStatus} role="status">
          {failure} The overlap list and the project table below work without the map.
        </div>
      ) : null}
      {failure ? (
        // The style's own attribution never loads when tiles fail; keep the credit visible anyway.
        <p className={s.attribution}>
          <a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> ©{" "}
          <a href="https://www.openmaptiles.org/" target="_blank" rel="noreferrer">OpenMapTiles</a> Data from{" "}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>
        </p>
      ) : null}
      <div className={s.legend} aria-label="Legend">
        <span>
          <i className={s.dot} style={{ background: COLORS.DESC }} /> Dominion Energy SC
        </span>
        <span>
          <i className={s.dot} style={{ background: COLORS.GPC }} /> Georgia Power
        </span>
        <span>
          <i className={s.dot} style={{ background: COLORS.unknown }} /> Owner unknown
        </span>
        <span>
          <i className={s.ring} /> Low-confidence location
        </span>
        <span>
          <i className={s.dash} /> Center-to-center, not a route
        </span>
        {selection ? (
          <button type="button" className={s.clear} onClick={() => onSelect(null)}>
            Clear selection
          </button>
        ) : null}
      </div>
    </div>
  );
}
