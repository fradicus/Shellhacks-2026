"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge, Button, EmptyState, Table, type Tone } from "@/components/ui";
import type { Brief, Extraction, ExtractionField, Source } from "@/lib/types";
import s from "./gemini.module.css";

export interface Card {
  key: string;
  sourceId: string;
  page: number;
  projectKey: string;
  name: string;
  rawText: string | null;
  flags: string[];
  deterministic: Record<string, unknown>;
}

const FIELDS: [string, string][] = [
  ["project_id", "Project ID"],
  ["name", "Name"],
  ["description", "Description"],
  ["need", "Need"],
  ["status", "Status"],
  ["in_service_raw", "In-service date (raw)"],
  ["total_cost", "Total cost"],
  ["yearly_spend", "Yearly spend"],
  ["endpoints", "Endpoints"],
  ["voltage_kv", "Voltage (kV)"],
];
const COST = new Set(["total_cost", "yearly_spend"]);
const COMPARISON_TONE: Record<string, Tone> = { match: "ok", mismatch: "warn", missing: "neutral" };
const STATUS_TONE: Record<string, Tone> = { accepted: "ok", rejected: "warn", failed: "warn" };

function fmt(field: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  const money = (n: unknown) =>
    typeof n === "number" ? n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : String(n);
  if (Array.isArray(v)) return v.length ? v.map((x) => (COST.has(field) ? money(x) : String(x))).join(" · ") : "—";
  if (typeof v === "object") return Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k}: ${money(x)}`).join(" · ");
  if (typeof v === "number") return COST.has(field) ? money(v) : v.toLocaleString("en-US");
  return String(v);
}

function asField(v: unknown): ExtractionField | null {
  return v && typeof v === "object" && "value" in (v as object) ? (v as ExtractionField) : null;
}

function Summary({ cards, extractions }: { cards: Card[]; extractions: Extraction[] }) {
  const processed = extractions.length;
  const models = [...new Set(extractions.map((e) => e.model))];
  const prompts = [...new Set(extractions.map((e) => e.prompt_version))];
  const status = (st: string) => extractions.filter((e) => (e.status ?? (e.accepted ? "accepted" : "rejected")) === st).length;
  if (processed === 0) {
    return (
      <section className={s.unavailable} role="status">
        <strong>Gemini extraction unavailable.</strong> 0 of {cards.length} DESC cards processed and no stored model output
        (live Gemini runs were deferred). Nothing on this page is presented as a Gemini result.
        {cards.length
          ? " The source text and the deterministic parse below are real; the Gemini column fills in once the pipeline's batch run is committed."
          : ""}
      </section>
    );
  }
  return (
    <section className={s.summary} aria-label="Extraction summary">
      <dl className={s.stats}>
        <div>
          <dt>Model</dt>
          <dd>{models.map((m) => <code key={m}>{m}</code>)}</dd>
        </div>
        <div>
          <dt>Prompt</dt>
          <dd>{prompts.map((p) => <code key={p}>{p}</code>)}</dd>
        </div>
        <div>
          <dt>Pages processed</dt>
          <dd className="num">
            {processed} / {cards.length}
          </dd>
        </div>
        <div>
          <dt>Accepted · rejected · failed</dt>
          <dd className="num">
            {status("accepted")} · {status("rejected")} · {status("failed")}
          </dd>
        </div>
      </dl>
      <Table caption="Validated field agreement with the deterministic parse (not independent human accuracy)">
        <thead>
          <tr>
            <th scope="col">Field</th>
            <th scope="col">Match (valid citation)</th>
            <th scope="col">Mismatch</th>
            <th scope="col">Missing</th>
            <th scope="col">Invalid</th>
            <th scope="col">Agreement</th>
          </tr>
        </thead>
        <tbody>
          {FIELDS.map(([f, label]) => {
            const c = { match: 0, mismatch: 0, missing: 0, invalid: 0 };
            for (const e of extractions) {
              const cmp = String(e.comparison[f] ?? "missing") as keyof typeof c;
              const fld = asField(e.fields[f]);
              if (cmp === "match" && fld?.valid) c.match++;
              else if (cmp in c) c[cmp === "match" ? "invalid" : cmp]++;
              if (fld && !fld.valid && cmp !== "match") c.invalid++;
            }
            return (
              <tr key={f}>
                <th scope="row">{label}</th>
                <td className="num">{c.match}</td>
                <td className="num">{c.mismatch}</td>
                <td className="num">{c.missing}</td>
                <td className="num">{c.invalid}</td>
                <td className="num">
                  {((c.match / processed) * 100).toFixed(1)}% <span className={s.muted}>({c.match}/{processed})</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </section>
  );
}

function CardView({ card, ext, source }: { card: Card; ext: Extraction | undefined; source: Source | undefined }) {
  const text = ext?.source_text ?? card.rawText;
  const pdf = source?.url ? `${source.url}#page=${card.page}` : null;
  const st = ext ? (ext.status ?? (ext.accepted ? "accepted" : "rejected")) : null;
  return (
    <div className={s.card}>
      <aside className={s.sourceCol} aria-label="Source page text">
        <h3>
          Source page text{" "}
          {pdf ? (
            <a href={pdf} target="_blank" rel="noreferrer">
              p. {card.page} ↗
            </a>
          ) : (
            <span>p. {card.page}</span>
          )}
        </h3>
        <p className={s.muted}>{ext?.source_text ? "Exactly the text Gemini was given." : "Text as extracted by the deterministic parser (F01)."}</p>
        {card.flags.length ? (
          <p className={s.flags}>
            Parser flags: {card.flags.map((f) => <code key={f}>{f}</code>)}
          </p>
        ) : null}
        <pre className={s.text}>{text ?? "No stored page text."}</pre>
      </aside>

      <section className={s.fieldsCol} aria-label="Gemini fields vs deterministic parse">
        <div className={s.cardHead}>
          <h3>{card.name}</h3>
          <code>{card.projectKey}</code>
          {st ? <Badge tone={STATUS_TONE[st] ?? "neutral"}>{st}</Badge> : <Badge tone="neutral">no Gemini output</Badge>}
          {ext ? (
            <span className={s.muted}>
              <code>{ext.model}</code> · prompt <code>{ext.prompt_version}</code>
              {ext.generated_at ? ` · ${ext.generated_at}` : ""}
            </span>
          ) : null}
        </div>
        {ext?.rejection_reason ? <p className={s.reason}>Rejected: {ext.rejection_reason}</p> : null}
        <table className={s.fields}>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Gemini (structured, with quote)</th>
              <th scope="col">Deterministic parse (F01)</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {FIELDS.map(([f, label]) => {
              const fld = asField(ext?.fields[f]);
              const cmp = ext ? String(ext.comparison[f] ?? "missing") : null;
              const det = ext?.deterministic?.[f] ?? card.deterministic[f];
              return (
                <tr key={f} data-result={!cmp ? "none" : cmp === "match" && fld && !fld.valid ? "invalid" : cmp}>
                  <th scope="row">{label}</th>
                  <td data-label="Gemini">
                    {!ext ? (
                      <em className="unknown">Not extracted</em>
                    ) : fld ? (
                      <>
                        <div>{fmt(f, fld.value)}</div>
                        {fld.quote ? <q className={s.quote}>{fld.quote}</q> : null}
                        {!fld.valid ? <div className={s.reason}>Invalid: {fld.reasons.join("; ") || "failed validation"}</div> : null}
                      </>
                    ) : (
                      <span className={s.muted}>—</span>
                    )}
                  </td>
                  <td data-label="Deterministic (F01)">{fmt(f, det)}</td>
                  <td data-label="Result">
                    {cmp ? (
                      <Badge tone={cmp === "match" && fld && !fld.valid ? "warn" : (COMPARISON_TONE[cmp] ?? "neutral")}>
                        {cmp === "match" && fld && !fld.valid ? "match, invalid cite" : cmp}
                      </Badge>
                    ) : (
                      <span className={s.muted}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Briefs({ briefs }: { briefs: Brief[] }) {
  if (!briefs.length) {
    return <EmptyState title="No briefs generated yet">Grounded briefs appear here once the brief pipeline (F12) has run.</EmptyState>;
  }
  return (
    <Table caption={`${briefs.length} generated brief${briefs.length === 1 ? "" : "s"}`}>
      <thead>
        <tr>
          <th scope="col">Pair</th>
          <th scope="col">Validation</th>
          <th scope="col">Model · prompt</th>
          <th scope="col">Generated</th>
        </tr>
      </thead>
      <tbody>
        {briefs.map((b) => (
          <tr key={b._id}>
            <td>
              <Link href={`/pair/${encodeURIComponent(b.match_id)}`}>{b.match_id}</Link>
            </td>
            <td>
              <Badge tone={b.validation === "passed" ? "ok" : "warn"}>{b.validation}</Badge>
              {b.rejection_reason ? <div className={s.reason}>{b.rejection_reason}</div> : null}
            </td>
            <td>
              <code>{b.model}</code> · <code>{b.prompt_version}</code>
            </td>
            <td className="num">{b.generated_at}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function Workbench({
  cards,
  extractions,
  sources,
  briefs,
}: {
  cards: Card[];
  extractions: Extraction[];
  sources: Source[];
  briefs: Brief[];
}) {
  const [tab, setTab] = useState<"extraction" | "briefs">("extraction");
  const byKey = useMemo(() => new Map(extractions.map((e) => [`${e.source_id}#${e.page}`, e])), [extractions]);
  const sourceIds = useMemo(() => [...new Set(cards.map((c) => c.sourceId))], [cards]);
  const first = cards.find((c) => byKey.has(c.key)) ?? cards[0];
  const [sourceId, setSourceId] = useState(first?.sourceId ?? "");
  const pages = cards.filter((c) => c.sourceId === sourceId);
  const [key, setKey] = useState(first?.key ?? "");
  const card = pages.find((c) => c.key === key) ?? pages[0];
  const label = (id: string) => {
    const src = sources.find((x) => x._id === id);
    return src?.filing ? `DESC filing ${src.filing}` : (src?.title ?? id);
  };

  return (
    <main className={s.page}>
      <header>
        <h1>Gemini workbench</h1>
        <p className={s.sub}>
          How Gemini&apos;s structured extraction of DESC project cards compares with the deterministic parser, field by field.
          Fields are accepted only if their quote is found on the cited page and the value agrees with the source. Georgia
          pages are never sent to Gemini (decision D2).
        </p>
        <div role="group" aria-label="Workbench views" className={s.tabs}>
          <Button aria-pressed={tab === "extraction"} onClick={() => setTab("extraction")}>
            Extraction
          </Button>
          <Button aria-pressed={tab === "briefs"} onClick={() => setTab("briefs")}>
            Briefs <span className="num">({briefs.length})</span>
          </Button>
        </div>
      </header>

      {tab === "briefs" ? (
        <Briefs briefs={briefs} />
      ) : (
        <>
          <Summary cards={cards} extractions={extractions} />
          {cards.length === 0 ? (
            <EmptyState title="No DESC cards">No DESC source pages are loaded, so there is nothing to compare.</EmptyState>
          ) : (
            <>
              <div className={s.picker}>
                <label>
                  Source{" "}
                  <select
                    value={sourceId}
                    onChange={(e) => {
                      setSourceId(e.target.value);
                      setKey("");
                    }}
                  >
                    {sourceIds.map((id) => (
                      <option key={id} value={id}>
                        {label(id)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Page{" "}
                  <select value={card?.key ?? ""} onChange={(e) => setKey(e.target.value)}>
                    {pages.map((c) => (
                      <option key={c.key} value={c.key}>
                        p. {c.page} · {c.name.slice(0, 70)}
                        {byKey.has(c.key) ? "" : " (no Gemini output)"}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              {card ? <CardView card={card} ext={byKey.get(card.key)} source={sources.find((x) => x._id === card.sourceId)} /> : null}
            </>
          )}
        </>
      )}
    </main>
  );
}
