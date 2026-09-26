"use client";

import Link from "next/link";
import { useMemo } from "react";
import type { Selection } from "@/components/map/MapView";
import { BandBadge, Button, EmptyState, ReviewBadge, UtilityBadge, fmtMiles, gapText } from "@/components/ui";
import type { MatchRow, Project, View } from "@/lib/types";
import s from "./list.module.css";

export type Order = "priority" | "distance";

function ProjectLine({ p, fallbackKey }: { p: Project | null; fallbackKey: string }) {
  return (
    <div className={s.project}>
      <UtilityBadge utility={p?.utility ?? "unknown"} />
      <span className={s.name}>{p?.name ?? fallbackKey}</span>
    </div>
  );
}

export function OverlapList({
  matches,
  view,
  viewLabel,
  order,
  onOrder,
  selection,
  onSelect,
}: {
  matches: MatchRow[];
  view: View;
  viewLabel: string;
  order: Order;
  onOrder: (o: Order) => void;
  selection: Selection;
  onSelect: (s: Selection) => void;
}) {
  // Priority order comes from the data (nearby-band-v1 `rank`); distance order reproduces the sponsor sheet.
  const rows = useMemo(() => {
    const byRank = [...matches].sort((x, y) => (x.rank ?? Infinity) - (y.rank ?? Infinity));
    return order === "priority" ? byRank : [...matches].sort((x, y) => x.distance_mi - y.distance_mi);
  }, [matches, order]);

  const isActive = (m: MatchRow) =>
    selection?.kind === "pair"
      ? selection.id === m._id
      : selection?.kind === "project"
        ? m.a === selection.key || m.b === selection.key
        : false;

  return (
    <section aria-label="Ranked overlaps" className={s.wrap}>
      <header className={s.head}>
        <h2>
          {rows.length} {viewLabel.toLowerCase()} overlap{rows.length === 1 ? "" : "s"}
        </h2>
        <div role="group" aria-label="Order" className={s.order}>
          <Button aria-pressed={order === "priority"} onClick={() => onOrder("priority")}>
            Priority
          </Button>
          <Button
            aria-pressed={order === "distance"}
            onClick={() => onOrder("distance")}
            title="Nearest first, as in the sponsor's overlap sheet"
          >
            Distance
          </Button>
        </div>
      </header>
      <p className={s.rule}>
        {order === "priority"
          ? "Priority: under 10 mi first, then 10–25 mi; within each, closest in-service dates first (unknown last), then distance."
          : "Distance order: nearest centers first."}
      </p>

      {rows.length === 0 ? (
        <EmptyState title={`No ${view} overlaps`}>
          Nothing in this view meets the rule. Zero is a valid answer, not an error.
        </EmptyState>
      ) : (
        <ol className={s.list}>
          {rows.map((m) => (
            <li key={m._id} className={`${s.row} ${isActive(m) ? s.active : ""}`}>
              <button
                type="button"
                className={s.select}
                onClick={() => onSelect({ kind: "pair", id: m._id })}
                aria-pressed={selection?.kind === "pair" && selection.id === m._id}
                aria-label={`Show on map: ${m.project_a?.name ?? m.a} and ${m.project_b?.name ?? m.b}, ${fmtMiles(m.distance_mi)}`}
              >
                <span className={s.rank} aria-hidden>
                  {order === "priority" ? (m.rank ?? "–") : ""}
                </span>
                <span className={s.body}>
                  <ProjectLine p={m.project_a} fallbackKey={m.a} />
                  <ProjectLine p={m.project_b} fallbackKey={m.b} />
                  <span className={s.facts}>
                    <strong className="num">{fmtMiles(m.distance_mi)}</strong>
                    <span className="num">{gapText(m.time_gap_days)}</span>
                    <BandBadge band={m.band} />
                    <ReviewBadge state={m.review_state} />
                  </span>
                </span>
              </button>
              <Link href={`/pair/${encodeURIComponent(m._id)}`} className={s.open}>
                Evidence <span aria-hidden>→</span>
                <span className="visually-hidden"> for this pair</span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
