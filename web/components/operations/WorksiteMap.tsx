"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap, Marker as MlMarker } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import styles from "./operations.module.css";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const US_BOUNDS: [[number, number], [number, number]] = [[-125, 24], [-66, 50]];

type MapHost = HTMLDivElement & { __worksiteMap?: MlMap };

export function WorksiteMap({
  lat,
  lon,
  onPick,
}: {
  lat: string;
  lon: string;
  onPick: (point: { lat: number; lon: number }) => void;
}) {
  const frame = useRef<MapHost>(null);
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const markerRef = useRef<MlMarker | null>(null);
  const pickRef = useRef(onPick);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    pickRef.current = onPick;
  }, [onPick]);

  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    let readyFallback: ReturnType<typeof setTimeout> | undefined;
    (async () => {
      try {
        const ml = await import("maplibre-gl");
        if (cancelled || !container.current || !frame.current) return;
        ml.setWorkerUrl(`https://cdn.jsdelivr.net/npm/maplibre-gl@${ml.getVersion()}/dist/maplibre-gl-worker.mjs`);
        map = new ml.Map({
          container: container.current,
          style: STYLE_URL,
          bounds: US_BOUNDS,
          fitBoundsOptions: { padding: 20 },
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        frame.current.__worksiteMap = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        // Register immediately: CI may never finish style/tile load, and Playwright can
        // click the canvas before a load-scoped handler would exist.
        map.on("click", (event) => {
          pickRef.current({ lat: event.lngLat.lat, lon: event.lngLat.lng });
        });
        const markReady = () => {
          if (cancelled || !map) return;
          map.getCanvas().style.cursor = "crosshair";
          setReady(true);
        };
        map.on("error", (event) => {
          const message = event.error?.message ?? "";
          if (/fetch|load|tile|style|NetworkError|Failed/i.test(message)) {
            setFailure("Basemap unavailable. Enter coordinates manually or retry later.");
            markReady();
          }
        });
        map.on("load", markReady);
        readyFallback = setTimeout(markReady, 2500);
      } catch (error) {
        setFailure(`Map unavailable (${error instanceof Error ? error.message : "unknown error"}).`);
      }
    })();
    return () => {
      cancelled = true;
      if (readyFallback) clearTimeout(readyFallback);
      if (frame.current?.__worksiteMap) delete frame.current.__worksiteMap;
      markerRef.current?.remove();
      markerRef.current = null;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const parsedLat = Number(lat);
    const parsedLon = Number(lon);
    if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLon)) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    void import("maplibre-gl").then((ml) => {
      if (mapRef.current !== map) return;
      if (!markerRef.current) markerRef.current = new ml.Marker({ color: "#b45309" }).setLngLat([parsedLon, parsedLat]).addTo(map);
      else markerRef.current.setLngLat([parsedLon, parsedLat]);
      map.easeTo({ center: [parsedLon, parsedLat], zoom: Math.max(map.getZoom(), 8), duration: 450 });
    });
  }, [lat, lon, ready]);

  return (
    <div className={styles.mapBlock}>
      <div
        ref={frame}
        className={styles.mapFrame}
        role="application"
        aria-label="Click the map to set the worksite coordinates"
        data-ready={ready ? "true" : "false"}
      >
        <div ref={container} className={styles.mapCanvas} />
        {!ready && !failure && <p className={styles.mapStatus}>Loading basemap…</p>}
        {failure && <p className={styles.mapStatus} role="status">{failure}</p>}
      </div>
      <p className={styles.mapHint}>Click the map to set latitude and longitude. Checking the worksite still requires a label and AEF year, then calls `/api/operations/site`.</p>
    </div>
  );
}
