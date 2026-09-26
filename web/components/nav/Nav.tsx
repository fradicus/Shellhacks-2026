"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Nav.module.css";

// Every route in the app, so no feature ever needs to edit the nav.
export const ROUTES = [
  { href: "/", label: "Overlaps" },
  { href: "/time", label: "Time view" },
  { href: "/changes", label: "Filing changes" },
  { href: "/coverage", label: "Coverage" },
  { href: "/gemini", label: "Gemini workbench" },
  { href: "/impact", label: "Impact" },
] as const;

export function Nav() {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" || path.startsWith("/pair/") : path.startsWith(href));
  return (
    <header className={`${styles.bar} no-print`}>
      <Link href="/" className={styles.brand}>
        GridBridge
      </Link>
      <nav aria-label="Main">
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
    </header>
  );
}
