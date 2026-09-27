"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONSource, Map as MlMap } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import type { WaterEvidence } from "./siteModel";
import s from "./impact.module.css";

/** Located project centers only (from the active dataset); unlocated projects are left off, never guessed. */
export type MapProject = { key: string; name: string; utility: string; lat: number; lon: number; confidence: string | null; inPair: boolean };
export type PickedPoint = { label: string; lat: number; lon: number };

// Same dark basemap as /time; marker colors are the site tokens in app/globals.css (--desc, --gpc, --unknown, --accent, --warn, --band0).
const STYLE_URL = "https://tiles.openfreemap.org/styles/dark";
const COLORS = { DESC: "#5cc8ff", GPC: "#ffae42", unknown: "#a3a8b6", accent: "#bfe9ff", picked: "#ff9a78", gauge: "#86e5cf", tide: "#c9a7ff", ink: "#06080d" };
const SOUTHEAST: [number, number, number, number] = [-85.6, 30.3, -78.5, 35.3];
const EMPTY = { type: "FeatureCollection" as const, features: [] };

/**
 * Click a project dot to snap to its located center, or click anywhere else to check that exact point.
 * The basemap comes from OpenFreeMap; every environmental lookup goes through our own /api/operations/site.
 */
export function SiteMap({ projects, point, water, onPick, onReport, loading }: { projects: MapProject[]; point: PickedPoint | null; water: NonNullable<WaterEvidence["data"]> | null; onPick: (p: PickedPoint) => void; onReport?: () => void; loading?: boolean }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const onPickRef = useRef(onPick);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [coverage, setCoverage] = useState(true);
  const [stationCount, setStationCount] = useState<number | null>(null);

  useEffect(() => { onPickRef.current = onPick; }, [onPick]);

  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const ml = await import("maplibre-gl");
        if (cancelled || !container.current) return;
        // Same worker workaround as components/map/MapView.tsx.
        ml.setWorkerUrl(`https://cdn.jsdelivr.net/npm/maplibre-gl@${ml.getVersion()}/dist/maplibre-gl-worker.mjs`);
        map = new ml.Map({ container: container.current, style: STYLE_URL, bounds: SOUTHEAST, fitBoundsOptions: { padding: 24 }, attributionControl: { compact: true } });
        mapRef.current = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.on("error", (e) => { if (/fetch|load|tile|style|NetworkError|Failed/i.test(e.error?.message ?? "")) setFailure("Basemap tiles failed to load. Use the buttons or coordinates instead."); });
        map.on("load", () => {
          if (!map) return;
          for (const id of ["stations", "projects", "picked", "gauges", "tide"]) map.addSource(id, { type: "geojson", data: EMPTY });
          // Coverage: every saved 10-year NOAA station, drawn faint and underneath so sites stay primary.
          map.addLayer({ id: "stations-reach", type: "circle", source: "stations", paint: { "circle-radius": ["interpolate", ["exponential", 2], ["zoom"], 3, 2, 6, 14, 9, 110], "circle-color": COLORS.accent, "circle-opacity": 0.05 } });
          map.addLayer({ id: "stations", type: "circle", source: "stations", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 1.2, 8, 3.5], "circle-color": COLORS.accent, "circle-opacity": 0.55 } });
          const tip = new ml.Popup({ closeButton: false, closeOnClick: false, className: s.stationPopup, offset: 8 });
          map.on("mouseenter", "stations", (e) => {
            const f = e.features?.[0]; if (!f || f.geometry.type !== "Point") return;
            const q = f.properties as { name: string; wind: boolean; snow: boolean };
            tip.setLngLat(f.geometry.coordinates as [number, number]).setText(`${q.name} · 10-yr NOAA record${q.wind ? " · wind" : ""}${q.snow ? " · snow" : ""}`).addTo(map!);
          });
          map.on("mouseleave", "stations", () => tip.remove());
          fetch("/api/weather-history/stations").then((r) => (r.ok ? r.json() : null)).then((body: { stations?: { id: string; name: string; lat: number; lon: number; wind: boolean; snow: boolean }[] } | null) => {
            if (!body?.stations || !map || cancelled) return;
            (map.getSource("stations") as GeoJSONSource).setData({ type: "FeatureCollection", features: body.stations.map((st) => ({ type: "Feature", geometry: { type: "Point", coordinates: [st.lon, st.lat] }, properties: { id: st.id, name: st.name, wind: st.wind, snow: st.snow } })) });
            setStationCount(body.stations.length);
          }).catch(() => { /* coverage layer is optional; lookups still work */ });
          const color = ["match", ["get", "utility"], "DESC", COLORS.DESC, "GPC", COLORS.GPC, COLORS.unknown];
          map.addLayer({ id: "pair-halo", type: "circle", source: "projects", filter: ["==", ["get", "inPair"], 1], paint: { "circle-radius": 14, "circle-color": COLORS.accent, "circle-opacity": 0.22, "circle-stroke-color": COLORS.accent, "circle-stroke-width": 1, "circle-stroke-opacity": 0.6 } });
          map.addLayer({
            id: "projects", type: "circle", source: "projects",
            paint: {
              "circle-radius": 6,
              "circle-color": ["case", ["==", ["get", "conf"], "low"], "rgba(0,0,0,0)", color] as never,
              "circle-stroke-color": ["case", ["==", ["get", "conf"], "low"], color, COLORS.ink] as never,
              "circle-stroke-width": ["case", ["==", ["get", "conf"], "low"], 2.5, 1.5],
            },
          });
          map.addLayer({ id: "gauges", type: "circle", source: "gauges", paint: { "circle-radius": 5, "circle-color": COLORS.gauge, "circle-stroke-color": COLORS.ink, "circle-stroke-width": 1.5 } });
          map.addLayer({ id: "tide", type: "circle", source: "tide", paint: { "circle-radius": 6, "circle-color": COLORS.tide, "circle-stroke-color": COLORS.ink, "circle-stroke-width": 1.5 } });
          map.addLayer({ id: "picked", type: "circle", source: "picked", paint: { "circle-radius": 9, "circle-color": "rgba(0,0,0,0)", "circle-stroke-color": COLORS.picked, "circle-stroke-width": 3 } });
          map.on("click", (e) => {
            const hit = map!.queryRenderedFeatures(e.point, { layers: ["projects"] })[0];
            if (hit && hit.geometry.type === "Point") {
              const [lon, lat] = hit.geometry.coordinates as [number, number];
              onPickRef.current({ label: `${String(hit.properties?.name ?? "Project")} center`, lat, lon }); // snap to the center, not the pixel
            } else onPickRef.current({ label: "Map point", lat: Math.round(e.lngLat.lat * 1e5) / 1e5, lon: Math.round(e.lngLat.lng * 1e5) / 1e5 });
          });
          map.on("mouseenter", "projects", () => (map!.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", "projects", () => (map!.getCanvas().style.cursor = "crosshair"));
          map.getCanvas().style.cursor = "crosshair";
          setReady(true);
        });
      } catch (err) {
        setFailure(`Map unavailable (${err instanceof Error ? err.message : "unknown error"}). Use the buttons or coordinates instead.`);
      }
    })();
    return () => { cancelled = true; map?.remove(); mapRef.current = null; };
  }, []);

  // Projects: fit to the pair when one is attached.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("projects") as GeoJSONSource).setData({ type: "FeatureCollection", features: projects.map((p) => ({
      type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      properties: { key: p.key, name: p.name, utility: p.utility, conf: p.confidence ?? "unknown", inPair: p.inPair ? 1 : 0 },
    })) });
    const pair = projects.filter((p) => p.inPair);
    if (pair.length) {
      const lons = pair.map((p) => p.lon), lats = pair.map((p) => p.lat);
      map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 90, maxZoom: 10, duration: 0 });
    }
  }, [ready, projects]);

  // Picked point plus the gauges and tide station that answered for it.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const pt = (lon: number, lat: number, properties: Record<string, unknown> = {}) => ({ type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [lon, lat] }, properties });
    (map.getSource("picked") as GeoJSONSource).setData({ type: "FeatureCollection", features: point ? [pt(point.lon, point.lat)] : [] });
    const gauges = water?.rivers?.gauges.slice(0, 3) ?? [];
    (map.getSource("gauges") as GeoJSONSource).setData({ type: "FeatureCollection", features: gauges.map((g) => pt(g.lon, g.lat, { id: g.site_id })) });
    const station = water?.tides?.station;
    (map.getSource("tide") as GeoJSONSource).setData({ type: "FeatureCollection", features: station ? [pt(station.lon, station.lat, { id: station.id })] : [] });
    if (point) map.easeTo({ center: [point.lon, point.lat], zoom: Math.max(map.getZoom(), 9) });
  }, [ready, point, water]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    for (const id of ["stations", "stations-reach"]) map.setLayoutProperty(id, "visibility", coverage ? "visible" : "none");
  }, [ready, coverage]);

  return <div className={s.siteMapWrap}>
    <div ref={container} className={s.siteMap} role="region" aria-label={`Site map with ${projects.length} located project centers. Click a project or any point to check site evidence; the buttons and coordinate fields do the same.`} />
    {!ready && !failure && <div className={s.siteMapStatus}>Loading map…</div>}
    {failure && <div className={s.siteMapStatus} role="status">{failure}</div>}
    {!point && ready && <div className={s.mapHint} aria-hidden>Click anywhere to drop a pin</div>}
    {point && onReport && <div className={s.mapAction}>
      <span>{point.label.length > 42 ? `${point.label.slice(0, 40)}…` : point.label}</span>
      <button type="button" onClick={onReport} disabled={loading}>{loading ? "Loading records…" : "Report this spot ↓"}</button>
    </div>}
    <ul className={s.legend} aria-label="Map legend">
      <li><i style={{ background: COLORS.DESC }} />DESC project</li>
      <li><i style={{ background: COLORS.GPC }} />Georgia Power project</li>
      <li><i className={s.legendRing} />Low-confidence location</li>
      <li><i className={s.legendHalo} />Selected pair</li>
      <li><i className={s.legendPicked} />Checked point</li>
      <li><i style={{ background: COLORS.gauge }} />USGS gauge</li>
      <li><i style={{ background: COLORS.tide }} />NOAA tide station</li>
      <li><label className={s.coverageToggle}><input type="checkbox" checked={coverage} onChange={(e) => setCoverage(e.target.checked)} /><i className={s.legendStation} />Saved 10-yr weather stations{stationCount !== null ? ` (${stationCount.toLocaleString("en-US")})` : ""}; anywhere else is looked up live</label></li>
    </ul>
  </div>;
}
