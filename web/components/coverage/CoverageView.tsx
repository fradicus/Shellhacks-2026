import { Badge, EmptyState, Table } from "@/components/ui";
import type { Coverage, Run, Source } from "@/lib/types";
import s from "./coverage.module.css";

type CountMap = Record<string, number>;
type Unlocated = { project_id: string; project_key: string; name: string };
type Gemini = {
  status?: string | null;
  reason?: string | null;
  measurement?: string | null;
  model?: string | null;
  live_calls?: number | null;
  corpus_pages?: number | null;
  pages_processed?: number | null;
  qa_checked?: number | null;
  per_field?: Record<string, FieldResult> | null;
};
type FieldResult = { accuracy?: number | null; denominator?: number | null };
type ManualAudit = {
  sample_count?: number | null;
  field_group_count?: number | null;
  agreements?: number | null;
  mismatches?: number | null;
  gemini_comparison?: { real_records?: number | null; accuracy?: number | null; status?: string | null } | null;
};
type Global = {
  project_versions?: number;
  active_projects?: number;
  location_records?: number;
  located_endpoints?: number;
  located_project_versions?: number;
  matches?: number;
  distinct_matched_project_versions?: number;
  raw_match_states?: CountMap;
  effective_match_states?: CountMap;
  audit_review_counts?: CountMap | null;
  manual_source_audit?: ManualAudit | null;
  gemini?: Gemini | null;
};
type Counts = {
  coverage_scope?: string;
  rows_seen?: number | null;
  rows_parsed?: number | null;
  project_versions?: number | null;
  active_projects?: number | null;
  inactive_projects?: number | null;
  filed_endpoint_projects_all_versions?: CountMap | null;
  location_records?: number | null;
  endpoint_confidence?: CountMap | null;
  located_endpoints?: number | null;
  located_active_projects?: number | null;
  unlocated_active_projects?: number | null;
  unlocated_active?: Unlocated[];
  flagged_versions?: number | null;
  quality_flags?: CountMap | null;
  distinct_matched_project_versions?: number | null;
  matches_involving_source?: number | null;
  effective_match_states?: CountMap | null;
  global?: Global;
};

export interface CoverageViewProps {
  coverage: Coverage[];
  sources: Source[];
  latestRun: Run | null;
}

const FIELD_LABELS: Record<string, string> = {
  project_id: "Project ID",
  name: "Name",
  description: "Description",
  need: "Need",
  status: "Status",
  in_service_raw: "In-service date",
  total_cost: "Total cost",
  yearly_spend: "Yearly spend",
  endpoints: "Endpoints",
  voltage_kv: "Voltage",
};

function n(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString("en-US") : "N/A";
}

function percent(value: number | null | undefined): string {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "N/A";
}

function ratio(value: number | null | undefined, total: number | null | undefined): number | null {
  return typeof value === "number" && typeof total === "number" && total > 0 ? value / total : null;
}

function Bar({ label, value, total }: { label: string; value?: number | null; total?: number | null }) {
  const share = ratio(value, total);
  return (
    <div className={s.barRow}>
      <div className={s.barLabel}>
        <span>{label}</span>
        <span className="num">{share === null ? "N/A" : `${n(value)} / ${n(total)} · ${percent(share)}`}</span>
      </div>
      <div className={s.track} aria-hidden="true">
        {share === null ? null : <span style={{ width: `${share * 100}%` }} />}
      </div>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value?: number; detail: string }) {
  return (
    <div className={s.metric}>
      <dt>{label}</dt>
      <dd className="num">{n(value)}</dd>
      <p>{detail}</p>
    </div>
  );
}

function SourceCard({ source, counts }: { source: Source; counts: Counts | undefined }) {
  if (!counts) {
    return (
      <article className={s.sourceCard}>
        <h3>{source._id}</h3>
        <EmptyState title="Coverage not available">No ledger record was generated for this source.</EmptyState>
      </article>
    );
  }
  if (counts.coverage_scope === "fixture_reference_only" || counts.coverage_scope === "not_ingested") {
    const fixture = counts.coverage_scope === "fixture_reference_only";
    return (
      <article className={s.sourceCard}>
        <div className={s.sourceHead}><div><h3>{source._id}</h3><p>{source.title}</p></div><Badge tone="neutral">{fixture ? "fixture reference" : "not ingested"}</Badge></div>
        <EmptyState title="Canonical coverage N/A">
          {fixture
            ? "This sponsor sample supports fixture demonstrations and has no canonical project records in the coverage ledger."
            : "No canonical project records are loaded for this source; its coverage is unavailable."}
        </EmptyState>
      </article>
    );
  }
  const flags = Object.entries(counts.quality_flags ?? {}).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const confidence = counts.endpoint_confidence ?? {};
  const filed = counts.filed_endpoint_projects_all_versions ?? {};
  return (
    <article className={s.sourceCard}>
      <div className={s.sourceHead}>
        <div>
          <h3>{source._id}</h3>
          <p>{source.title}</p>
        </div>
        <Badge tone={source._id.startsWith("desc") ? "desc" : source._id.startsWith("gpc") ? "gpc" : "neutral"}>
          {n(counts.project_versions)} versions
        </Badge>
      </div>
      <div className={s.bars}>
        <Bar label="Canonical rows parsed" value={counts.rows_parsed} total={counts.rows_seen} />
        <Bar label="Active projects located" value={counts.located_active_projects} total={counts.active_projects} />
        <Bar label="Active projects in a match" value={counts.distinct_matched_project_versions} total={counts.active_projects} />
      </div>
      <dl className={s.compactStats}>
        <div><dt>Active · inactive</dt><dd>{n(counts.active_projects)} · {n(counts.inactive_projects)}</dd></div>
        <div><dt>Location records</dt><dd>{n(counts.location_records)}</dd></div>
        <div><dt>Accepted endpoints</dt><dd>{n(counts.located_endpoints)}</dd></div>
        <div><dt>Filed projects (2 · 1 · 0 endpoints)</dt><dd>{n(filed["2"])} · {n(filed["1"])} · {n(filed["0"])}</dd></div>
        <div><dt>High · medium · low · rejected</dt><dd>{n(confidence.high)} · {n(confidence.medium)} · {n(confidence.low)} · {n(confidence.rejected)}</dd></div>
        <div><dt>Flagged versions</dt><dd>{n(counts.flagged_versions)}</dd></div>
        <div><dt>Matches involving source</dt><dd>{n(counts.matches_involving_source)}</dd></div>
      </dl>
      <div className={s.flags} aria-label={`${source._id} quality flags`}>
        {flags.length ? flags.map(([flag, count]) => <code key={flag}>{flag} · {count}</code>) : <span>No quality flags.</span>}
      </div>
      <details className={s.unlocated}>
        <summary>{n(counts.unlocated_active_projects)} active projects without an accepted location</summary>
        {(counts.unlocated_active ?? []).length ? (
          <ul>{counts.unlocated_active!.map((project) => <li key={project.project_id}><code>{project.project_key}</code> {project.name}</li>)}</ul>
        ) : <p>None.</p>}
      </details>
    </article>
  );
}

function RunStatus({ latestRun }: { latestRun: Run | null }) {
  return (
    <section className={s.run} aria-labelledby="dataset-status">
      <div>
        <h2 id="dataset-status">Dataset status</h2>
        <p><strong>Coverage shown:</strong> records selected from the active dataset.</p>
      </div>
      <div>
        <h3>Latest load attempt</h3>
        {latestRun ? (
          <p>
            <Badge tone={latestRun.status === "ok" ? "ok" : "warn"}>{latestRun.status}</Badge>{" "}
            <code>{latestRun.dataset ?? "dataset not recorded"}</code> · {latestRun.started_at}
          </p>
        ) : <p>N/A — no load attempt is available.</p>}
        <p className={s.note}>The latest attempt is reported separately; a failed attempt does not replace the active dataset.</p>
      </div>
    </section>
  );
}

function Accuracy({ gemini, manual }: { gemini: Gemini | null | undefined; manual: ManualAudit | null | undefined }) {
  const fields = Object.entries(gemini?.per_field ?? {});
  const displayFields: [string, FieldResult][] = fields.length
    ? fields
    : Object.keys(FIELD_LABELS).map((field) => [field, {}]);
  const reason = gemini?.reason === "live_execution_not_requested"
    ? "Live execution was not requested."
    : gemini?.reason ?? "No extraction evaluation artifact is available.";
  return (
    <section className={s.quality} aria-labelledby="validation-heading">
      <h2 id="validation-heading">Validation evidence</h2>
      <div className={s.evidenceGrid}>
        <article>
          <h3>Gemini extraction</h3>
          <p>
            Model <strong>{gemini?.model ?? "N/A"}</strong> · live calls <strong>{n(gemini?.live_calls)}</strong> · pages processed{" "}
            <strong>{n(gemini?.pages_processed)} / {n(gemini?.corpus_pages)}</strong>
          </p>
          <p className={s.note}>{reason}</p>
        </article>
        <article>
          <h3>Independent source spot check</h3>
          <p>
            <strong>{n(manual?.agreements)} agreements</strong> across {n(manual?.sample_count)} records and{" "}
            {n(manual?.field_group_count)} field groups; {n(manual?.mismatches)} mismatches.
          </p>
          <p className={s.note}>This F13 source check is separate from model accuracy. Real Gemini comparison accuracy: N/A.</p>
        </article>
      </div>
      <Table caption="Validated Gemini field agreement with the deterministic parser; N/A means no real model output">
        <thead><tr><th scope="col">Field</th><th scope="col">Denominator</th><th scope="col">Agreement</th></tr></thead>
        <tbody>
          {displayFields.map(([field, result]) => (
            <tr key={field}>
              <th scope="row">{FIELD_LABELS[field] ?? field}</th>
              <td className="num">{n(result.denominator)}</td>
              <td className="num">{percent(result.accuracy)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </section>
  );
}

export function CoverageView({ coverage, sources, latestRun }: CoverageViewProps) {
  if (!coverage.length) {
    return (
      <main className={s.page}>
        <h1>Data quality</h1>
        <EmptyState title="Coverage ledger unavailable">
          No source coverage records are loaded. This is unavailable data, not zero projects or zero matches.
        </EmptyState>
      </main>
    );
  }
  const counts = new Map(coverage.map((row) => [row._id, row.counts as Counts]));
  const first = counts.values().next().value as Counts | undefined;
  const global = first?.global ?? {};
  const effective = global.effective_match_states ?? {};
  const audit = global.audit_review_counts;
  return (
    <main className={s.page}>
      <header className={s.hero}>
        <div>
          <p className={s.eyebrow}>Coverage ledger · committed public sources</p>
          <h1>Data quality</h1>
          <p>
            Every count keeps its denominator. Project versions, active records, endpoint evidence and matches stay separate
            so incomplete coverage cannot read as zero opportunity.
          </p>
        </div>
        <div className={s.reviewBox}>
          <span>Effective match review</span>
          <strong>{n(effective.rejected)} rejected · {n(effective.needs_review)} need review</strong>
          <small>{audit ? `${n(audit.downgraded)} audit downgrades (${n(audit.pairs)} pairs, ${n(audit.endpoints)} endpoints)` : "Audit evidence N/A"}</small>
        </div>
      </header>

      <dl className={s.metrics}>
        <Metric label="Project versions" value={global.project_versions} detail={`${n(global.active_projects)} active`} />
        <Metric label="Location records" value={global.location_records} detail={`${n(global.located_endpoints)} accepted endpoints`} />
        <Metric label="Located projects" value={global.located_project_versions} detail="current filing versions" />
        <Metric label="Matches" value={global.matches} detail={`${n(global.distinct_matched_project_versions)} distinct projects`} />
      </dl>

      <RunStatus latestRun={latestRun} />

      <section aria-labelledby="sources-heading">
        <h2 id="sources-heading">Source inventory</h2>
        <Table caption="Public source identity and scope">
          <thead><tr><th scope="col">Source</th><th scope="col">Filing</th><th scope="col">Pages</th><th scope="col">Status</th><th scope="col">SHA-256</th></tr></thead>
          <tbody>{sources.map((source) => (
            <tr key={source._id}>
              <th scope="row">{source._id}<div className={s.publisher}>{source.publisher}</div></th>
              <td>{source.filing ?? "N/A"}</td><td className="num">{n(source.pages)}</td><td>{source.public_status}</td>
              <td><code>{source.sha256.slice(0, 12)}…</code></td>
            </tr>
          ))}</tbody>
        </Table>
      </section>

      <section aria-labelledby="source-coverage-heading">
        <h2 id="source-coverage-heading">Coverage by source</h2>
        <div className={s.sourceGrid}>{sources.map((source) => <SourceCard key={source._id} source={source} counts={counts.get(source._id)} />)}</div>
      </section>

      <Accuracy gemini={global.gemini} manual={global.manual_source_audit} />
    </main>
  );
}
