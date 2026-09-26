// Shared primitives. Frozen after F00.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Utility } from "@/lib/types";
import s from "./ui.module.css";

export type Tone = "neutral" | "desc" | "gpc" | "unknown" | "band0" | "band1" | "warn" | "ok";

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span className={`${s.badge} ${s[tone]}`} title={title}>
      {children}
    </span>
  );
}

export const UTILITY_LABEL: Record<Utility, string> = {
  DESC: "Dominion Energy SC",
  GPC: "Georgia Power",
  unknown: "Owner unknown",
};

export function UtilityBadge({ utility }: { utility: Utility }) {
  const tone: Tone = utility === "DESC" ? "desc" : utility === "GPC" ? "gpc" : "unknown";
  return <Badge tone={tone}>{UTILITY_LABEL[utility]}</Badge>;
}

export function Button({
  variant = "default",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" }) {
  return (
    <button
      type="button"
      {...props}
      className={[s.button, variant === "primary" ? s.primary : "", className ?? ""].join(" ").trim()}
    />
  );
}

/** Class for links styled as buttons. */
export const buttonClass = s.button;

export function Table({ caption, children }: { caption?: ReactNode; children: ReactNode }) {
  return (
    <div className={s.tableWrap}>
      <table className={s.table}>
        {caption ? <caption>{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={s.state} role="status">
      <strong>{title}</strong>
      {children}
    </div>
  );
}

export function ErrorState({ title = "Data unavailable", children }: { title?: string; children?: ReactNode }) {
  return (
    <div className={`${s.state} ${s.error}`} role="alert">
      <strong>{title}</strong>
      {children ?? "The database could not be reached. Nothing is shown rather than stale or sample data."}
    </div>
  );
}

/** A null value, drawn: hatched and labeled "unknown" (or a more specific word). Never an empty cell. */
export function Unknown({ children = "unknown", title }: { children?: ReactNode; title?: string }) {
  return (
    <em className="unknown" title={title}>
      {children}
    </em>
  );
}

/** A figure read off an instrument: large display number, mono unit, optional label above and note below.
 *  `value` null renders Unknown; callers pass stored values only. */
export function Readout({
  label,
  value,
  unit,
  note,
  size = "m",
}: {
  label?: ReactNode;
  value: ReactNode | null;
  unit?: ReactNode;
  note?: ReactNode;
  size?: "s" | "m" | "l";
}) {
  const sizeClass = size === "s" ? s.readoutS : size === "l" ? s.readoutL : "";
  return (
    <span className={`${s.readout} ${sizeClass}`}>
      {label ? <span className={s.readoutLabel}>{label}</span> : null}
      {value === null ? (
        <span className={`${s.readoutValue} ${s.isUnknown}`}>
          <Unknown />
        </span>
      ) : (
        <span className={`${s.readoutValue} num`}>
          {value}
          {unit ? <small>{unit}</small> : null}
        </span>
      )}
      {note ? <span className={s.readoutNote}>{note}</span> : null}
    </span>
  );
}

// --- display formatting (display only; never used to decide eligibility) ------------------------------------------------

/** Distances are stored unrounded; round to 2 dp only for display. */
export function fmtMiles(mi: number): string {
  return `${mi.toFixed(2)} mi`;
}

/** "in service 152 days apart" or "date unknown". Never "built at the same time". */
export function gapText(days: number | null): string {
  if (days === null) return "date unknown";
  if (days === 0) return "same in-service date";
  return `in service ${days.toLocaleString("en-US")} day${days === 1 ? "" : "s"} apart`;
}

export function bandLabel(band: 0 | 1): string {
  return band === 0 ? "< 10 mi" : "10–25 mi";
}

export function BandBadge({ band }: { band: 0 | 1 }) {
  return <Badge tone={band === 0 ? "band0" : "band1"}>{bandLabel(band)}</Badge>;
}

export function ReviewBadge({ state }: { state?: string }) {
  if (state === "confirmed") return <Badge tone="ok">Reviewed</Badge>;
  if (state === "rejected") return <Badge tone="warn">Rejected in review</Badge>;
  return <Badge tone="neutral">Needs review</Badge>;
}
