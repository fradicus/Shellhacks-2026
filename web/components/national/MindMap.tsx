"use client";

import { useMemo, useState } from "react";
import { Badge, EmptyState } from "@/components/ui";
import {
  MIND_MAP_PLACE_PREVIEW,
  type MindMapPlaceNode,
  type MindMapRegionNode,
  type MindMapStateNode,
  type MindMapTree,
} from "@/lib/national/mindmap";
import { BarChart, DonutChart } from "./SimpleCharts";
import s from "./national.module.css";

const n = (value: number) => value.toLocaleString("en-US");

function PlaceBlock({
  place,
  onSelectProject,
}: {
  place: MindMapPlaceNode;
  onSelectProject: (project: { id: string; nativeId: string; name: string }) => void;
}) {
  const [expanded, setExpanded] = useState(place.projectCount <= MIND_MAP_PLACE_PREVIEW);
  const visible = expanded ? place.projects : place.projects.slice(0, MIND_MAP_PLACE_PREVIEW);
  const placeKind = place.kind === "facility" ? "facility site" : place.kind === "county" ? "county" : "place unknown";
  return (
    <div className={s.mmPlace}>
      <div className={s.mmPlaceHead}>
        <span>
          <strong>{place.label}</strong>
          <small>{placeKind}</small>
        </span>
        <span className={s.mmCount}>
          <Badge tone={place.locatedCount ? "ok" : "warn"}>{n(place.projectCount)} electrical</Badge>
        </span>
      </div>
      <ul className={s.mmProjects}>
        {visible.map((project) => (
          <li key={project.id}>
            <button type="button" className={s.mmProject} onClick={() => onSelectProject(project)}>
              <span>
                <strong>{project.name}</strong>
                <small>{project.owner ?? "Owner not reported"} · {project.statusLabel}</small>
              </span>
              <Badge tone={project.located ? "ok" : "warn"}>{project.located ? "point known" : "location unknown"}</Badge>
            </button>
          </li>
        ))}
        {!expanded && place.projects.length > visible.length ? (
          <li>
            <button type="button" className={s.mmMore} onClick={() => setExpanded(true)}>
              Show all {n(place.projects.length)} electrical projects
            </button>
          </li>
        ) : null}
      </ul>
    </div>
  );
}

function StateBlock({
  state,
  onSelectProject,
}: {
  state: MindMapStateNode;
  onSelectProject: (project: { id: string; nativeId: string; name: string }) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className={s.mmState}>
      <button type="button" className={s.mmStateHead} onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className={s.mmStateDot} aria-hidden="true" />
        <span>
          <strong>{state.name}</strong>
          <small>{n(state.places.length)} places · {n(state.locatedCount)} evidenced points</small>
        </span>
        <strong className={s.mmCountNum}>{n(state.projectCount)}</strong>
      </button>
      {open ? (
        <div className={s.mmPlaces}>
          {state.places.map((place) => (
            <PlaceBlock key={place.id} place={place} onSelectProject={onSelectProject} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function RegionCircle({
  region,
  onSelectProject,
}: {
  region: MindMapRegionNode;
  onSelectProject: (project: { id: string; nativeId: string; name: string }) => void;
}) {
  const [open, setOpen] = useState(region.code !== "unknown");
  return (
    <article className={s.mmRegion}>
      <button type="button" className={s.mmRegionHead} onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className={s.mmRegionCircle} aria-hidden="true">
          <span>{n(region.projectCount)}</span>
        </span>
        <span>
          <strong>{region.name}</strong>
          <small>Census region circle · {n(region.states.length)} states · {n(region.locatedCount)} located</small>
        </span>
      </button>
      {open ? (
        <div className={s.mmStates}>
          {region.states.map((state) => (
            <StateBlock key={state.code} state={state} onSelectProject={onSelectProject} />
          ))}
        </div>
      ) : null}
    </article>
  );
}

export function MindMap({
  tree,
  loading,
  error,
  onSelectProject,
  onRetry,
}: {
  tree: MindMapTree | null;
  loading: boolean;
  error: string | null;
  onSelectProject: (project: { id: string; nativeId: string; name: string }) => void;
  onRetry: () => void;
}) {
  const summary = useMemo(() => {
    if (!tree) return null;
    return {
      regions: tree.regions.length,
      states: tree.regions.reduce((sum, region) => sum + region.states.length, 0),
      places: tree.regions.reduce(
        (sum, region) => sum + region.states.reduce((inner, state) => inner + state.places.length, 0),
        0,
      ),
    };
  }, [tree]);

  if (loading) {
    return (
      <section className={s.mindMap} aria-busy="true" aria-label="Mind map">
        <p className={s.banner} role="status">Building region → state → place → electrical hierarchy…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className={s.mindMap} aria-label="Mind map">
        <EmptyState title="Mind map unavailable">{error} <button type="button" className={s.mmMore} onClick={onRetry}>Retry</button></EmptyState>
      </section>
    );
  }

  if (!tree || tree.meta.included === 0) {
    return (
      <section className={s.mindMap} aria-label="Mind map">
        <EmptyState title="No hierarchy to draw">
          No imported project records match the current filters. Unknown geography stays unknown and is not filled from Census boundaries.
        </EmptyState>
      </section>
    );
  }

  return (
    <section className={s.mindMap} aria-label="Mind map">
      <div className={s.mmIntro}>
        <div>
          <p className={s.eyebrow}>Simple hierarchy</p>
          <h2>Region circle → state → place → electrical</h2>
          <p>
            Showing {n(tree.meta.included)} of {n(tree.meta.total)} filtered records
            {summary ? ` across ${n(summary.regions)} regions, ${n(summary.states)} states, and ${n(summary.places)} places` : ""}.
            New imports land in the same four levels without extra chrome.
          </p>
        </div>
        {tree.meta.truncated ? (
          <p className={s.note} role="status">
            Safety limit reached at {n(tree.meta.limit)} records. Narrow filters to see the rest.
          </p>
        ) : null}
      </div>

      <div className={s.chartGrid} aria-label="Mind map charts">
        <DonutChart title="Projects by Census region" slices={tree.charts.byRegion} />
        <BarChart title="Projects by status" slices={tree.charts.byStatus} />
        <BarChart title="Top reported owners" slices={tree.charts.byOwner} />
      </div>

      <div className={s.mmTree}>
        {tree.regions.map((region) => (
          <RegionCircle key={region.code} region={region} onSelectProject={onSelectProject} />
        ))}
      </div>

      <ul className={s.mmNotes}>
        {tree.meta.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
