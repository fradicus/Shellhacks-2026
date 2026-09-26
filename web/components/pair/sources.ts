import type { Project, Source } from "@/lib/types";

export interface Citation {
  label: string;
  title?: string;
  /** Only DESC filings link out (public PDF, `#page=N`); Georgia cites the page number only (decision D2). */
  href?: string;
}

export function cite(project: Pick<Project, "utility">, sources: Source[] | undefined, sourceId: string, page: number | null | undefined): Citation {
  const src = sources?.find((s) => s._id === sourceId);
  const doc = src?.filing ? `${project.utility === "unknown" ? src.publisher : project.utility} filing ${src.filing}` : (src?.title ?? sourceId);
  const label = `${doc}${page ? `, p. ${page}` : ""}`;
  const linkable = project.utility === "DESC" && src?.url && src.public_status === "public";
  return { label, title: src?.title, href: linkable ? (page ? `${src.url}#page=${page}` : src.url) : undefined };
}
