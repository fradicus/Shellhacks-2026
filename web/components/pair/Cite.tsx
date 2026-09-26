import type { Citation } from "./sources";

export function Cite({ c }: { c: Citation }) {
  return c.href ? (
    <a href={c.href} target="_blank" rel="noreferrer">
      {c.label}
    </a>
  ) : (
    <span>{c.label}</span>
  );
}
