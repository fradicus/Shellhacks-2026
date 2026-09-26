import type { Citation } from "./sources";
import s from "./cite.module.css";

/**
 * A citation link with a quiet "source peek": on hover or keyboard focus, after a beat, a small card shows the source,
 * the stored quote when there is one (never invented), and where the page can be opened. CSS only; hover devices only.
 */
export function Cite({ c, quote }: { c: Citation; quote?: string | null }) {
  const text = quote?.trim();
  return (
    <span className={`${s.cite} ${c.href ? s.linked : ""}`}>
      {c.href ? (
        <a href={c.href} target="_blank" rel="noreferrer">
          {c.label}
        </a>
      ) : (
        <span>{c.label}</span>
      )}
      <span className={s.peek} aria-hidden="true">
        <span className={s.src}>{c.title ?? c.label}</span>
        {text ? <span className={s.quote}>“{text}”</span> : null}
        <span className={s.foot}>
          {c.href ? `Open ${c.page ? `page ${c.page}` : "the filing"} ↗` : `${c.page ? `Page ${c.page} · ` : ""}page number only; not linked (decision D2)`}
        </span>
      </span>
    </span>
  );
}
