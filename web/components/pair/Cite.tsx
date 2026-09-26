import type { Citation } from "./sources";

export function Cite({ c }: { c: Citation }) {
  return c.href ? (
    <a href={c.href} target="_blank" rel="noreferrer" title={c.title}>
      {c.label}
    </a>
  ) : (
    <span title={c.title}>{c.label}</span>
  );
}
