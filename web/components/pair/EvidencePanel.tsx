import { Badge, UtilityBadge } from "@/components/ui";
import type { Location, Project, Source, VersionChange } from "@/lib/types";
import { Cite } from "./Cite";
import { cite } from "./sources";
import s from "./pair.module.css";

const NOT_PUBLISHED = <span className={s.unknown}>Not published</span>;
const NEEDS_REVIEW = <span className={s.unknown}>Needs review</span>;

const FIELD_LABEL: Record<string, string> = {
  name: "Project name",
  native_id: "Project ID",
  description: "Description",
  need: "Need",
  status: "Status",
  in_service: "In-service date",
  cost_usd: "Estimated cost (as filed)",
  voltages_kv: "Voltage",
  endpoints: "Endpoints (as filed)",
};

const usd = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function fieldValue(p: Project, field: string): React.ReactNode {
  switch (field) {
    case "in_service":
      return p.in_service.raw ?? NOT_PUBLISHED;
    case "cost_usd":
      return typeof p.cost_usd === "number" ? usd(p.cost_usd) : NOT_PUBLISHED;
    case "voltages_kv": {
      const v = (p as unknown as { voltages_kv?: number[] }).voltages_kv;
      return v?.length ? v.map((x) => `${x} kV`).join(", ") : NOT_PUBLISHED;
    }
    case "endpoints":
      return p.filed_endpoints?.map((e) => e.name).join(" · ") || NOT_PUBLISHED;
    default: {
      const v = (p as unknown as Record<string, unknown>)[field];
      return v === null || v === undefined || v === "" ? NOT_PUBLISHED : String(v);
    }
  }
}

const show = (v: unknown) => (v === null || v === undefined ? "—" : typeof v === "number" ? v.toLocaleString("en-US") : String(v));

function osmHref(l: Location): string | null {
  if (l.osm_url) return l.osm_url;
  if (l.osm_id) {
    const [type, id] = l.osm_id.includes("/") ? l.osm_id.split("/") : ["node", l.osm_id];
    return `https://www.openstreetmap.org/${type}/${id}`;
  }
  return null;
}

function Endpoint({ l }: { l: Location }) {
  const href = osmHref(l);
  const tone = l.confidence === "high" ? "ok" : l.confidence === "medium" ? "band1" : "warn";
  return (
    <li className={s.endpoint}>
      <div className={s.endpointHead}>
        <strong>{l.name}</strong>
        <Badge tone={tone}>{l.confidence} confidence</Badge>
      </div>
      <div className="num">
        {l.lat !== undefined && l.lon !== undefined ? `${l.lat.toFixed(5)}, ${l.lon.toFixed(5)}` : NEEDS_REVIEW}
        {href ? (
          <>
            {" · "}
            <a href={href} target="_blank" rel="noreferrer">
              OpenStreetMap {l.osm_id ?? ""}
            </a>
          </>
        ) : null}
      </div>
      <div className={s.muted}>{l.evidence}</div>
    </li>
  );
}

function Endpoints({ p }: { p: Project }) {
  const all = p.endpoints ?? [];
  const accepted = all.filter((l) => l.confidence !== "rejected");
  const rejected = all.filter((l) => l.confidence === "rejected");
  const basis = p.center?.basis;
  return (
    <section>
      <h4>Endpoint locations</h4>
      {accepted.length ? <ul className={s.endpoints}>{accepted.map((l) => <Endpoint key={l._id ?? `${l.endpoint_index}-${l.name}`} l={l} />)}</ul> : <p>{NEEDS_REVIEW}: no located endpoint.</p>}
      {rejected.length ? (
        <details className={s.rejected}>
          <summary>
            {rejected.length} rejected or unlocated candidate{rejected.length === 1 ? "" : "s"}
          </summary>
          <ul className={s.endpoints}>
            {rejected.map((l) => (
              <li key={l._id ?? `${l.endpoint_index}-${l.name}`} className={s.endpoint}>
                <strong>{l.name}</strong> <span className={s.muted}>{l.evidence}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      <p className={s.basis}>
        <strong>Center:</strong>{" "}
        {p.center
          ? `${p.center.lat.toFixed(5)}, ${p.center.lon.toFixed(5)}, ${basis === "one" ? "from one located endpoint" : "mean of two located endpoints"}`
          : "no center (no located endpoint), so this project can't be matched spatially"}
      </p>
    </section>
  );
}

export function EvidencePanel({
  p,
  side,
  sources,
  changes,
}: {
  p: Project;
  side: "A" | "B";
  sources?: Source[];
  changes: VersionChange[];
}) {
  const src = cite(p, sources, p.source.source_id, p.source.page);
  const evidence = p.field_evidence ?? {};
  const fields = Object.keys(FIELD_LABEL).filter((f) => f in evidence);
  return (
    <article className={s.panel} aria-labelledby={`p-${side}`}>
      <header className={s.panelHead}>
        <span className={s.side}>{side}</span>
        <div>
          <h3 id={`p-${side}`}>{p.name}</h3>
          <div className={s.idLine}>
            <UtilityBadge utility={p.utility} />
            <code>{p.project_key}</code>
            {p.active ? null : <Badge tone="warn">superseded filing</Badge>}
          </div>
        </div>
      </header>

      <dl className={s.facts}>
        <dt>Source</dt>
        <dd>
          <Cite c={src} />
          {p.utility === "GPC" && p.source.page ? <span className={s.muted}> (page number only; decision D2)</span> : null}
        </dd>
        <dt>Native ID</dt>
        <dd className="mono">{p.native_id}</dd>
        <dt>Owner code</dt>
        <dd>
          {p.owner_code ? <code>{p.owner_code}</code> : NOT_PUBLISHED}
          {p.owner_basis ? <span className={s.muted}> · utility from {p.owner_basis}</span> : null}
        </dd>
        <dt>In service</dt>
        <dd>
          <span className="num">{p.in_service.raw ?? "Not published"}</span>{" "}
          <span className={s.muted}>
            ({p.in_service.precision === "day" ? `exact date ${p.in_service.date}` : `${p.in_service.precision} precision; no exact date`})
          </span>
        </dd>
        {p.status ? (
          <>
            <dt>Status</dt>
            <dd>{p.status}</dd>
          </>
        ) : null}
      </dl>

      <Endpoints p={p} />

      {fields.length ? (
        <section>
          <h4>Values as filed</h4>
          <table className={s.evidence}>
            <tbody>
              {fields.map((f) => (
                <tr key={f}>
                  <th scope="row">{FIELD_LABEL[f]}</th>
                  <td>
                    <div>{fieldValue(p, f)}</div>
                    <details className={s.quote}>
                      <summary>
                        <Cite c={cite(p, sources, p.source.source_id, evidence[f].page)} />
                      </summary>
                      <q>{evidence[f].quote}</q>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      <section>
        <h4>Filing changes</h4>
        {changes.length ? (
          <ul className={s.changes}>
            {changes.map((c) => (
              <li key={c._id}>
                <code>{c.field}</code>: <span className="num">{show(c.old)}</span> →{" "}
                <span className="num">{show(c.new)}</span>
                <div className={s.muted}>
                  <Cite c={cite(p, sources, c.from_source, c.from_page)} /> → <Cite c={cite(p, sources, c.to_source, c.to_page)} />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className={s.muted}>No changes recorded between filings.</p>
        )}
      </section>

      {p.raw_text ? (
        <details className={s.raw}>
          <summary>Raw source text</summary>
          <pre>{p.raw_text}</pre>
        </details>
      ) : null}
    </article>
  );
}
