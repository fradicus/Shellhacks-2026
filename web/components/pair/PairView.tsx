import Link from "next/link";
import { Badge, BandBadge, ReviewBadge, UtilityBadge, fmtMiles, gapText } from "@/components/ui";
import type { PairDetail, Project } from "@/lib/types";
import { CoordinationCard } from "./CoordinationCard";
import { EvidencePanel } from "./EvidencePanel";
import s from "./pair.module.css";

function Missing({ k }: { k: string }) {
  return (
    <article className={s.panel}>
      <h3>
        <code>{k}</code>
      </h3>
      <p className={s.unknown}>Project record not found in the active dataset. Needs review.</p>
    </article>
  );
}

function Name({ p, k, side }: { p: Project | null; k: string; side: "A" | "B" }) {
  return (
    <div className={s.pairName} data-utility={p?.utility ?? "unknown"}>
      <span className={s.sideTag} aria-hidden="true">
        {side}
      </span>
      <UtilityBadge utility={p?.utility ?? "unknown"} />
      <span className={s.nameText}>{p?.name ?? k}</span>
    </div>
  );
}

export function PairView({ detail }: { detail: PairDetail }) {
  const { match: m, a, b, brief, version_changes, sources } = detail;
  const changesFor = (key: string) => version_changes.filter((c) => c.project_key === key);
  return (
    <main className={s.page}>
      <nav className="no-print" aria-label="Breadcrumb">
        <Link href={`/time?pair=${encodeURIComponent(m._id)}`}>← All overlaps</Link>
      </nav>

      <header className={s.header}>
        <div className={s.names}>
          <Name p={a} k={m.a} side="A" />
          <Name p={b} k={m.b} side="B" />
        </div>
        <div className={s.headline}>
          <span className={s.big + " num"}>{fmtMiles(m.distance_mi)}</span>
          <span className="num">{gapText(m.time_gap_days)}</span>
          <BandBadge band={m.band} />
          <ReviewBadge state={m.review_state} />
          <Badge tone="neutral">{m.view}</Badge>
          {m.rank ? <Badge tone="neutral">rank {m.rank}</Badge> : null}
        </div>
        <p className={s.muted}>
          Pair <code>{m._id}</code>. A coordination lead worth a planner&apos;s conversation, not a compliance finding or a
          savings estimate.
        </p>
      </header>

      <CoordinationCard m={m} a={a} b={b} brief={brief} />

      <h2 className={s.sectionTitle}>Evidence</h2>
      <div className={s.panels}>
        {a ? <EvidencePanel p={a} side="A" sources={sources} changes={changesFor(m.a)} /> : <Missing k={m.a} />}
        {b ? <EvidencePanel p={b} side="B" sources={sources} changes={changesFor(m.b)} /> : <Missing k={m.b} />}
      </div>
    </main>
  );
}
