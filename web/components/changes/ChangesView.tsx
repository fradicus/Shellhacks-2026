"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Cite } from "@/components/pair/Cite";
import { cite } from "@/components/pair/sources";
import { Badge, Button, EmptyState, UtilityBadge } from "@/components/ui";
import type { Source, Utility, VersionChange } from "@/lib/types";
import s from "./changes.module.css";

const LIMIT = 200;
const VERIFIED = "DESC:0139 M,N";
type Filter = "all" | "in_service" | "cost" | "status" | "other";
const FILTERS: { id: Filter; label: string; test: (f: string) => boolean }[] = [
  { id: "all", label: "All fields", test: () => true },
  { id: "in_service", label: "In-service date", test: (f) => f.startsWith("in_service") },
  { id: "cost", label: "Cost", test: (f) => f.startsWith("cost") },
  { id: "status", label: "Status", test: (f) => f === "status" },
  { id: "other", label: "Other", test: (f) => !f.startsWith("in_service") && !f.startsWith("cost") && f !== "status" },
];
const FIELD_LABEL: Record<string, string> = {
  "in_service.date": "In-service date",
  cost_usd: "Estimated cost",
  status: "Status",
  name: "Project name",
};

const isIsoDate = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
const days = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86_400_000);

function show(field: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "not published";
  if (typeof v === "number" && field.startsWith("cost")) return v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  if (typeof v === "number") return v.toLocaleString("en-US");
  return String(v);
}

function Delta({ c, analysisDate }: { c: VersionChange; analysisDate: string }) {
  if (c.field === "in_service.date" && isIsoDate(c.old) && isIsoDate(c.new)) {
    const d = days(c.old, c.new);
    const historical = c.old < analysisDate && c.new < analysisDate;
    return (
      <>
        <span className={s.delta}>
          filed date moved {Math.abs(d).toLocaleString("en-US")} days {d >= 0 ? "later" : "earlier"} between filings
        </span>
        {historical ? (
          <Badge tone="neutral" title={`Both dates are before the analysis date ${analysisDate}`}>
            historical
          </Badge>
        ) : null}
      </>
    );
  }
  if (c.field.startsWith("cost") && typeof c.old === "number" && typeof c.new === "number" && c.old !== 0) {
    const pct = ((c.new - c.old) / c.old) * 100;
    return <span className={s.delta}>{`${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% as filed`}</span>;
  }
  return null;
}

function ChangeRow({ c, utility, sources, analysisDate }: { c: VersionChange; utility: Utility; sources: Source[]; analysisDate: string }) {
  const p = { utility };
  return (
    <li className={s.change}>
      <div className={s.field}>{FIELD_LABEL[c.field] ?? c.field}</div>
      <div className={s.values}>
        <span className={s.old}>{show(c.field, c.old)}</span>
        <span aria-hidden>→</span>
        <span className="visually-hidden">changed to</span>
        <span className={s.new}>{show(c.field, c.new)}</span>
        <Delta c={c} analysisDate={analysisDate} />
      </div>
      <div className={s.cites}>
        <Cite c={cite(p, sources, c.from_source, c.from_page)} /> → <Cite c={cite(p, sources, c.to_source, c.to_page)} />
      </div>
    </li>
  );
}

export function ChangesView({
  changes,
  sources,
  names,
  inMatches,
  analysisDate,
}: {
  changes: VersionChange[];
  sources: Source[];
  names: Record<string, { name: string; utility: string }>;
  inMatches: Record<string, string[]>;
  analysisDate: string;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const test = FILTERS.find((f) => f.id === filter)!.test;
  const filtered = useMemo(() => changes.filter((c) => test(c.field)), [changes, test]);
  const shown = filtered.slice(0, LIMIT);

  const groups = useMemo(() => {
    const by = new Map<string, VersionChange[]>();
    for (const c of shown) by.set(c.project_key, [...(by.get(c.project_key) ?? []), c]);
    return [...by.entries()].sort(([a], [b]) => (a === VERIFIED ? -1 : b === VERIFIED ? 1 : a.localeCompare(b)));
  }, [shown]);

  const count = (f: Filter) => changes.filter((c) => FILTERS.find((x) => x.id === f)!.test(c.field)).length;
  const projectsChanged = new Set(changes.map((c) => c.project_key)).size;

  return (
    <main className={s.page}>
      <header className={s.head}>
        <h1>Filing changes</h1>
        <p className={s.sub}>
          The same project compared across two filings: {changes.length} changed field{changes.length === 1 ? "" : "s"} on{" "}
          {projectsChanged} project{projectsChanged === 1 ? "" : "s"}. A changed in-service date is a change in the filing,
          not evidence of a current delay.
        </p>
        <div role="group" aria-label="Filter by field" className={s.filters}>
          {FILTERS.map((f) => (
            <Button key={f.id} aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
              {f.label} <span className="num">({count(f.id)})</span>
            </Button>
          ))}
        </div>
        {filtered.length > LIMIT ? (
          <p className={s.sub} role="status">
            Showing the first {LIMIT} of {filtered.length} changes.
          </p>
        ) : null}
      </header>

      {groups.length === 0 ? (
        <EmptyState title="No filing changes">
          {changes.length ? "No changes for this field." : "No version changes have been recorded between filings."}
        </EmptyState>
      ) : (
        <ol className={s.groups}>
          {groups.map(([key, cs]) => {
            const meta = names[key];
            const utility = (meta?.utility ?? key.split(":")[0] ?? "unknown") as Utility;
            const pairs = inMatches[key] ?? [];
            return (
              <li key={key} className={`${s.group} ${key === VERIFIED ? s.verified : ""}`}>
                <div className={s.groupHead}>
                  <UtilityBadge utility={["DESC", "GPC"].includes(utility) ? utility : "unknown"} />
                  {meta ? <strong>{meta.name}</strong> : null}
                  <code>{key}</code>
                  {key === VERIFIED ? <Badge tone="ok">verified example</Badge> : null}
                  {pairs.length ? (
                    <Link href={`/pair/${encodeURIComponent(pairs[0])}`} className={s.inMatch}>
                      in {pairs.length} overlap{pairs.length === 1 ? "" : "s"} →
                    </Link>
                  ) : (
                    <span className={s.noMatch}>no overlap</span>
                  )}
                </div>
                <ul className={s.changes}>
                  {cs.map((c) => (
                    <ChangeRow key={c._id} c={c} utility={utility} sources={sources} analysisDate={analysisDate} />
                  ))}
                </ul>
              </li>
            );
          })}
        </ol>
      )}
    </main>
  );
}
