"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import s from "./impact.module.css";

export type SitePoint = {
  label: string;
  lat: number;
  lon: number;
};

type PhSample = { value: number; top: number | null; bottom: number | null; method: string };
type PointSummary = {
  label: string;
  lat: number;
  lon: number;
  loading: boolean;
  error: string | null;
  ph: PhSample | null;
  phNote: string | null;
  flood: string | null;
  wetland: string | null;
  gauges: number | null;
};

const YEAR = 2025;

function firstPh(soil: unknown): { ph: PhSample | null; note: string | null } {
  const units = (soil as { data?: { map_units?: { components?: { horizons?: { ph_h2o_1_to_1: number | null; depth_top_cm: number | null; depth_bottom_cm: number | null; ph_method: string }[] }[] }[] } } | null)?.data?.map_units ?? [];
  for (const unit of units) {
    for (const component of unit.components ?? []) {
      for (const horizon of component.horizons ?? []) {
        if (horizon.ph_h2o_1_to_1 != null) {
          return {
            ph: {
              value: horizon.ph_h2o_1_to_1,
              top: horizon.depth_top_cm,
              bottom: horizon.depth_bottom_cm,
              method: horizon.ph_method,
            },
            note: null,
          };
        }
      }
    }
  }
  return { ph: null, note: units.length ? "No pH in survey for this map unit" : "Soil survey unavailable" };
}

function waterBits(water: unknown): { flood: string | null; wetland: string | null; gauges: number | null } {
  const data = (water as { water?: { data?: {
    rivers?: { gauges?: unknown[] } | null;
    flood?: { zones?: { zone: string | null; special_flood_hazard_area: boolean | null }[] } | null;
    wetlands?: { mapped: boolean; features?: { wetland_type: string | null }[] } | null;
  } | null } })?.water?.data;
  if (!data) return { flood: "Flood zone unknown", wetland: "Wetland map unavailable", gauges: null };
  const zone = data.flood?.zones?.[0];
  const flood = zone
    ? `Flood zone ${zone.zone ?? "unknown"}${zone.special_flood_hazard_area ? " · special flood hazard area" : ""}`
    : "Flood zone unknown — no FEMA polygon at this point";
  const wetland = data.wetlands
    ? (data.wetlands.mapped
      ? `Wetland mapped${data.wetlands.features?.[0]?.wetland_type ? ` · ${data.wetlands.features[0].wetland_type}` : ""}`
      : "No mapped wetland at this point")
    : "Wetland map unavailable";
  return { flood, wetland, gauges: data.rivers?.gauges?.length ?? 0 };
}

async function loadPoint(point: SitePoint, signal: AbortSignal): Promise<Omit<PointSummary, "loading">> {
  const siteQs = new URLSearchParams({ lat: String(point.lat), lon: String(point.lon), year: String(YEAR) });
  const waterQs = new URLSearchParams({ lat: String(point.lat), lon: String(point.lon) });
  try {
    const [siteRes, waterRes] = await Promise.all([
      fetch(`/api/operations/site?${siteQs}`, { signal, cache: "no-store" }),
      fetch(`/api/operations/water?${waterQs}`, { signal, cache: "no-store" }),
    ]);
    if (!siteRes.ok) throw new Error(`Site evidence unavailable (${siteRes.status})`);
    const site = await siteRes.json();
    const { ph, note } = firstPh(site.soil);
    let flood: string | null = null;
    let wetland: string | null = null;
    let gauges: number | null = null;
    if (waterRes.ok) {
      const bits = waterBits(await waterRes.json());
      flood = bits.flood;
      wetland = bits.wetland;
      gauges = bits.gauges;
    } else {
      flood = "Water context unavailable";
      wetland = null;
    }
    return { label: point.label, lat: point.lat, lon: point.lon, error: null, ph, phNote: note, flood, wetland, gauges };
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    return {
      label: point.label, lat: point.lat, lon: point.lon, error: (error as Error).message,
      ph: null, phNote: null, flood: null, wetland: null, gauges: null,
    };
  }
}

export function SiteEvidence({ points }: { points: SitePoint[] }) {
  const [rows, setRows] = useState<PointSummary[]>(() => points.map((point) => ({
    label: point.label, lat: point.lat, lon: point.lon, loading: true, error: null,
    ph: null, phNote: null, flood: null, wetland: null, gauges: null,
  })));

  useEffect(() => {
    if (!points.length) return;
    const controller = new AbortController();
    setRows(points.map((point) => ({
      label: point.label, lat: point.lat, lon: point.lon, loading: true, error: null,
      ph: null, phNote: null, flood: null, wetland: null, gauges: null,
    })));
    void Promise.all(points.map(async (point) => {
      try {
        return { ...(await loadPoint(point, controller.signal)), loading: false };
      } catch {
        return null;
      }
    })).then((results) => {
      if (controller.signal.aborted) return;
      setRows(results.filter((row): row is PointSummary => row !== null));
    });
    return () => controller.abort();
  }, [points]);

  if (!points.length) return null;

  return (
    <section className={s.section} aria-labelledby="site-evidence-heading">
      <span className="eyebrow">01b / Worksite survey context</span>
      <h2 id="site-evidence-heading">Check the ground before you price mats.</h2>
      <p className={s.muted}>
        Public survey and water layers for each project center. This is screening context for the conversation —
        not a soil suitability call, flood determination, or wetland delineation. Numbers stay empty when the
        source has no value.
      </p>
      <div className={s.siteGrid}>
        {rows.map((row) => {
          const ops = `/operations?lat=${encodeURIComponent(String(row.lat))}&lon=${encodeURIComponent(String(row.lon))}&label=${encodeURIComponent(row.label)}&year=${YEAR}`;
          return (
            <article className={s.siteCard} key={`${row.label}-${row.lat}-${row.lon}`}>
              <span className="eyebrow">{row.label}</span>
              <h3>{row.lat.toFixed(4)}, {row.lon.toFixed(4)}</h3>
              {row.loading && <p className={s.muted}>Loading site and water evidence…</p>}
              {row.error && <p className={s.warning} role="status">{row.error}</p>}
              {!row.loading && !row.error && (
                <ul className={s.siteFacts}>
                  <li>
                    <strong>Soil pH (survey estimate)</strong>
                    <span>
                      {row.ph
                        ? `pH ${row.ph.value.toFixed(1)} · ${row.ph.method} · depth ${row.ph.top ?? "?"}-${row.ph.bottom ?? "?"} cm`
                        : row.phNote ?? "No data"}
                    </span>
                  </li>
                  <li>
                    <strong>Nearby gauges</strong>
                    <span>{row.gauges == null ? "No data" : row.gauges === 0 ? "None in search radius" : `${row.gauges} reported`}</span>
                  </li>
                  <li>
                    <strong>Flood / wetland</strong>
                    <span>{[row.flood, row.wetland].filter(Boolean).join(" · ") || "No data"}</span>
                  </li>
                </ul>
              )}
              <Link href={ops}>Open Field planning for this worksite →</Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
