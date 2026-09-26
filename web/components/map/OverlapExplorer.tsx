"use client";

import { useMemo, useState } from "react";
import { OverlapList, type Order } from "@/components/list/OverlapList";
import { ProjectTable } from "@/components/list/ProjectTable";
import { Badge, Button } from "@/components/ui";
import type { MatchRow, Project, View } from "@/lib/types";
import { MapView, type Selection } from "./MapView";
import s from "./map.module.css";

const VIEW_LABEL: Record<View, string> = { future: "Future", historical: "Historical", tentative: "Tentative" };
const VIEW_HELP: Record<View, string> = {
  future: "Both in-service dates exact and on/after the analysis date; locations high or medium confidence.",
  historical: "At least one in-service date is before the analysis date.",
  tentative: "A low-confidence location or an in-service date that isn't exact.",
};

export function OverlapExplorer(props: {
  matches: MatchRow[];
  projects: Project[];
  /** Older filing versions of these projects, not shown as current projects. */
  superseded: number;
  counts: Record<View, number>;
  initialView: View;
  analysisDate: string;
  sources: string[];
  fixtureMode: boolean;
}) {
  const { matches, projects, superseded, counts, initialView, analysisDate, sources, fixtureMode } = props;
  const [view, setView] = useState<View>(initialView);
  const [order, setOrder] = useState<Order>("priority");
  const [selection, setSelection] = useState<Selection>(null);

  const visible = useMemo(() => matches.filter((m) => m.view === view), [matches, view]);

  const changeView = (v: View) => {
    setView(v);
    setSelection(null);
  };

  return (
    <main className={s.page}>
      <section className={s.strip} aria-label="View and data version">
        <div className={s.title}>
          <h1>Transmission overlaps</h1>
          <p className={s.sub}>
            Dominion Energy SC and Georgia Power projects whose centers are less than 25 miles apart. Geography decides the
            overlap; in-service dates only rank it.
          </p>
        </div>
        <div className={s.controls}>
          <div role="group" aria-label="View" className={s.toggle}>
            {(Object.keys(VIEW_LABEL) as View[]).map((v) => (
              <Button key={v} aria-pressed={view === v} onClick={() => changeView(v)} title={VIEW_HELP[v]}>
                {VIEW_LABEL[v]} <span className="num">({counts[v]})</span>
              </Button>
            ))}
          </div>
          <dl className={s.meta}>
            <div>
              <dt>Analysis date</dt>
              <dd className="num">{analysisDate}</dd>
            </div>
            <div>
              <dt>Sources</dt>
              <dd>{sources.length ? sources.map((id) => <code key={id}>{id}</code>) : "none"}</dd>
            </div>
          </dl>
          {fixtureMode ? (
            <Badge tone="warn" title="DATA_MODE=fixture: the sponsor sample, not the database">
              Sample data (fixture mode)
            </Badge>
          ) : null}
        </div>
      </section>
      {initialView !== "future" && counts.future === 0 && view === initialView ? (
        <p className={s.note} role="status">
          No future overlaps in this data, so the {VIEW_LABEL[view].toLowerCase()} view is open. Zero future overlaps is a
          valid result.
        </p>
      ) : null}

      <div className={s.layout}>
        <div className={s.mapCol}>
          <MapView projects={projects} matches={visible} selection={selection} onSelect={setSelection} />
        </div>
        <div className={s.listCol}>
          <OverlapList
            matches={visible}
            view={view}
            viewLabel={VIEW_LABEL[view]}
            order={order}
            onOrder={setOrder}
            selection={selection}
            onSelect={setSelection}
          />
        </div>
      </div>

      <ProjectTable projects={projects} superseded={superseded} />
    </main>
  );
}
