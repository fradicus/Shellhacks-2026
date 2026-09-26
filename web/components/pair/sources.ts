import type { Project, Source } from "@/lib/types";

export interface Citation {
  label: string;
  /** Only DESC filings link out (public PDF, `#page=N`); Georgia cites the page number only (decision D2). */
  href?: string;
}

export function sourceTitle(sources: Source[] | undefined, id: string): string {
  return sources?.find((s) => s._id === id)?.title ?? id;
}

export function cite(project: Pick<Project, "utility">, sources: Source[] | undefined, sourceId: string, page: number | null | undefined): Citation {
  const src = sources?.find((s) => s._id === sourceId);
  const label = `${src?.title ?? sourceId}${page ? `, p. ${page}` : ""}`;
  const linkable = project.utility === "DESC" && src?.url && src.public_status === "public";
  return linkable ? { label, href: page ? `${src.url}#page=${page}` : src.url } : { label };
}
