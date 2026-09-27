"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import styles from "./Nav.module.css";

// Every route in the app, so no feature ever needs to edit the nav. The time view is the app's overlap surface
// (F21); "/" is the marketing home.
export const ROUTES = [
  { href: "/", label: "Home" },
  { href: "/time", label: "Overlaps" },
  { href: "/history", label: "History" },
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

// Server render has no layout to measure; fall back to useEffect there.
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

export function Nav() {
  const path = usePathname();
  const active = (href: string) =>
    href === "/" ? path === "/" : href === "/time" ? path.startsWith("/time") || path.startsWith("/pair/") : path.startsWith(href);
  const scroller = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);
  // The pill sits under the active tab, slides to whichever tab is hovered, and returns on leave.
  const [pill, setPill] = useState<{ x: number; w: number; shown: boolean; animate: boolean }>({ x: 0, w: 0, shown: false, animate: false });

  const moveTo = useCallback((el: HTMLElement | null | undefined, animate = true) => {
    if (!el) return setPill((p) => ({ ...p, shown: false }));
    setPill({ x: el.offsetLeft, w: el.offsetWidth, shown: true, animate });
  }, []);
  const current = useCallback(() => track.current?.querySelector<HTMLElement>('[aria-current="page"]'), []);

  useIsoLayoutEffect(() => {
    const el = current();
    moveTo(el, pill.shown);
    // Keep the active tab in view when the row scrolls on narrow screens.
    const box = scroller.current;
    if (el && box && box.scrollWidth > box.clientWidth) {
      box.scrollTo({ left: el.offsetLeft - (box.clientWidth - el.offsetWidth) / 2, behavior: pill.shown ? "smooth" : "auto" });
    }
    // Only the route should re-run this; pill.shown just picks instant placement on first paint.
  }, [path, current, moveTo]);

  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const ro = new ResizeObserver(() => moveTo(current(), false));
    ro.observe(el);
    return () => ro.disconnect();
  }, [current, moveTo]);

  return (
    <header className={`${styles.bar} no-print`}>
      <Link href="/" className={styles.brand}>
        <Mark />
        <span>Common Ground</span>
      </Link>
      <nav aria-label="Main" className={styles.nav} ref={scroller}>
        <div className={styles.track} ref={track} onMouseLeave={() => moveTo(current())}>
          <span
            className={styles.pill}
            aria-hidden="true"
            data-shown={pill.shown || undefined}
            data-animate={pill.animate || undefined}
            style={{ transform: `translateX(${pill.x}px)`, width: pill.w }}
          />
          <ul className={styles.links}>
            {ROUTES.map((r) => (
              <li key={r.href}>
                <Link
                  href={r.href}
                  className={styles.link}
                  aria-current={active(r.href) ? "page" : undefined}
                  onMouseEnter={(e) => moveTo(e.currentTarget)}
                  onFocus={(e) => moveTo(e.currentTarget)}
                  onBlur={() => moveTo(current())}
                >
                  {r.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </nav>
    </header>
  );
}
