"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Nav.module.css";

// Every route in the app, so no feature ever needs to edit the nav. The time view is the app's overlap surface
// (F21); "/" is the marketing home.
export const ROUTES = [
  { href: "/", label: "Home" },
  { href: "/time", label: "Overlaps" },
  { href: "/map", label: "Project map" },
  { href: "/explore", label: "National explorer" },
  { href: "/operations", label: "Field planning" },
  { href: "/changes", label: "Filing changes" },
  { href: "/coverage", label: "Coverage" },
  { href: "/gemini", label: "Gemini workbench" },
  { href: "/impact", label: "Impact" },
] as const;

/** Two service areas whose circles overlap: the product in one mark. */
export function Mark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" className={styles.mark}>
      <circle cx="9" cy="12" r="6.5" fill="none" stroke="var(--desc)" strokeWidth="1.6" />
      <circle cx="15" cy="12" r="6.5" fill="none" stroke="var(--gpc)" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="1.6" fill="var(--text)" />
    </svg>
  );
}

export function Nav() {
  const path = usePathname();
  const active = (href: string) =>
    href === "/" ? path === "/" : href === "/time" ? path.startsWith("/time") || path.startsWith("/pair/") : path.startsWith(href);
  return (
    <header className={`${styles.bar} no-print`}>
      <Link href="/" className={styles.brand}>
        <Mark />
        <span>GridBridge</span>
      </Link>
      <nav aria-label="Main" className={styles.nav}>
        <ul className={styles.links}>
          {ROUTES.map((r) => (
            <li key={r.href}>
              <Link href={r.href} className={styles.link} aria-current={active(r.href) ? "page" : undefined}>
                {r.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <span className={styles.scope} aria-hidden="true">
        <i style={{ background: "var(--desc)" }} />
        DESC
        <b>×</b>
        <i style={{ background: "var(--gpc)" }} />
        GPC
      </span>
    </header>
  );
}
