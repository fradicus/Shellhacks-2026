"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJSONSource, Map as MlMap } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import type { GeoBounds, NationalProject } from "@/lib/national/types";
import { displayPoints } from "@/lib/national/locations";
import s from "./national.module.css";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const STATUS_COLORS: Record<string, string> = {
  planned: "#2563eb",
  under_construction: "#ea580c",
  proposed: "#7c5b12",
  in_service: "#166534",
  cancelled: "#71717a",
  unknown: "#71717a",
};
const US_BOUNDS: [[number, number], [number, number]] = [[-170, 17], [-64, 72]];

export function NationalMap({
  projects,
  selectedId,
  focusBounds,
  emptyMessage,
  onSelect,
}: {
  projects: NationalProject[];
  selectedId: string | null;
  focusBounds: GeoBounds | null;
  emptyMessage?: string;
  onSelect(id: string): void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const selectRef = useRef(onSelect);
  const selectedRef = useRef(selectedId);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    selectRef.current = onSelect;
    selectedRef.current = selectedId;
  }, [onSelect, selectedId]);

  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    (async () => {
      try {
        const ml = await import("maplibre-gl");
        if (cancelled || !container.current) return;
        ml.setWorkerUrl(`https://cdn.jsdelivr.net/npm/maplibre-gl@${ml.getVersion()}/dist/maplibre-gl-worker.mjs`);
        map = new ml.Map({
          container: container.current,
          style: STYLE_URL,
          bounds: US_BOUNDS,
          fitBoundsOptions: { padding: 24 },
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.on("error", (event) => {
          const message = event.error?.message ?? "";
          if (/fetch|load|tile|style|NetworkError|Failed/i.test(message)) setFailure("Basemap unavailable. The project table still contains every result.");
        });
        map.on("load", () => {
          if (!map) return;
          map.addSource("national-projects", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
          map.addLayer({
            id: "national-project-halo",
            type: "circle",
            source: "national-projects",
            filter: ["==", ["get", "selected"], 1],
            paint: { "circle-radius": 13, "circle-color": "#facc15", "circle-opacity": 0.62 },
          });
          map.addLayer({
            id: "national-projects",
            type: "circle",
            source: "national-projects",
            paint: {
              "circle-radius": 7,
              "circle-color": ["get", "color"],
              "circle-opacity": ["case", ["==", ["get", "approximate"], 1], 0.15, ["==", ["get", "review"], "confirmed"], 0.9, 0.58],
              "circle-stroke-color": ["case", ["==", ["get", "review"], "confirmed"], "#ffffff", ["get", "color"]],
              "circle-stroke-width": ["case", ["==", ["get", "review"], "confirmed"], 1.5, 2.5],
            },
          });
          map.on("click", "national-projects", (event) => {
            const ids = [...new Set(event.features?.map((f) => f.properties?.id).filter((id): id is string => typeof id === "string"))];
            if (ids.length) {
              const current = selectedRef.current;
              selectRef.current(ids[(ids.indexOf(current ?? "") + 1) % ids.length]);
            }
          });
          map.on("mouseenter", "national-projects", () => (map!.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", "national-projects", () => (map!.getCanvas().style.cursor = ""));
          setReady(true);
        });
      } catch (error) {
        setFailure(`Map unavailable (${error instanceof Error ? error.message : "unknown error"}).`);
      }
    })();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("national-projects") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: projects.flatMap((project) => displayPoints(project).map((point) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [point.lon, point.lat] },
        properties: {
          id: project._id,
          selected: project._id === selectedId ? 1 : 0,
          review: project.location_review,
          approximate: project.center === null ? 1 : 0,
          color: STATUS_COLORS[project.status_group] ?? STATUS_COLORS.unknown,
        },
      }))),
    });

    if (focusBounds) {
      map.fitBounds(
        [[focusBounds.fit_west, focusBounds.south], [focusBounds.fit_east_unwrapped, focusBounds.north]],
        { padding: 34, maxZoom: 8 },
      );
      return;
    }
    const points = projects.flatMap((project) => displayPoints(project).map((point) => [point.lon, point.lat] as [number, number]));
    if (points.length === 1) map.easeTo({ center: points[0], zoom: 7 });
    else if (points.length > 1) {
      const lons = points.map(([lon]) => lon);
      const lats = points.map(([, lat]) => lat);
      map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 34, maxZoom: 8 });
    } else map.fitBounds(US_BOUNDS, { padding: 24 });
  }, [focusBounds, projects, ready, selectedId]);

  return (
    <section className={s.mapWrap} aria-label="Filtered national projects map">
      <div ref={container} className={s.map} />
      {failure || emptyMessage ? <p className={s.mapStatus} role="status">{failure ?? emptyMessage}</p> : null}
      <div className={s.legend} aria-label="Map legend">
        <span><i className={`${s.dot} ${s.planned}`} /> Planned</span>
        <span><i className={`${s.dot} ${s.construction}`} /> Under construction</span>
        <span><i className={s.ring} /> Tentative location</span>
        <span><i className={s.ring} style={{ opacity: 0.4 }} /> County reference · exact site unknown</span>
        <span>Click shared dots again to select another project; all remain in the list.</span>
      </div>
      <p className={s.attribution}><a href="https://openfreemap.org/" target="_blank" rel="noreferrer">OpenFreeMap</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap</a></p>
    </section>
  );
}
