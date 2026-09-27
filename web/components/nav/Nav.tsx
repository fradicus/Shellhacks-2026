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
  if (path === "/") return (
    <header className={`${styles.landingBar} no-print`}>
      <a href="#main-content" className={styles.skip}>Skip to content</a>
      <Link href="/" className={styles.landingBrand} aria-label="GridBridge home">
        <svg width="26" height="22" viewBox="0 0 28 24" fill="none" aria-hidden="true"><path d="M4 17C8 5 20 5 24 17M4 17h20" stroke="currentColor" strokeWidth="1.5"/><circle cx="4" cy="17" r="2.5" fill="currentColor"/><circle cx="24" cy="17" r="2.5" fill="currentColor"/></svg>
        GridBridge
      </Link>
      <nav aria-label="Main" className={styles.landingLinks}>
        <a href="#how-it-works">How it works</a>
        <a href="#the-corridor">The corridor</a>
        <a href="#workspace">Workspace</a>
      </nav>
      <Link href="/time" className={styles.launch}>Launch explorer <span aria-hidden="true">↗</span></Link>
    </header>
  );
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
