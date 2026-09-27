"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { RULE_MI, type Scope } from "./scope";
import s from "./time.module.css";

export type ScopeTab = "places" | "grid";
/** `scope: null` is the whole country. */
export interface ScopeOption { tab: ScopeTab; group: string | null; scope: Scope | null; label: string; hint?: string; count: number }

const TABS: { tab: ScopeTab; label: string }[] = [{ tab: "places", label: "Places" }, { tab: "grid", label: "Grid" }];

/**
 * "Which part of the map" (F19 spec 15): places for anyone, grid plans for people who know them, one search over
 * both. The pin is its own button beside it, because it is picked on the map, not from a list.
 */
export function ScopeBar({ current, count, total, options, unplanned, initialTab, pinArmed, onPick, onClear, onPin }: {
  current: string | null;
  count: number;
  total: number;
  options: ScopeOption[];
  /** Drawn projects with no grid plan on file, said out loud at the end of the Grid tab. */
  unplanned: number;
  initialTab: ScopeTab;
  pinArmed: boolean;
  onPick(scope: Scope): void;
  onClear(): void;
  onPin(armed: boolean): void;
}) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<ScopeTab>("places");
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();

  // Typing searches both tabs; otherwise the tab decides.
  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    return t ? options.filter((o) => o.label.toLowerCase().includes(t) || o.hint?.toLowerCase() === t) : options.filter((o) => o.tab === tab);
  }, [options, q, tab]);
  const max = Math.max(total, 1);
  const runs = useMemo(() => {
    const out: { group: string | null; items: { o: ScopeOption; i: number }[] }[] = [];
    shown.forEach((o, i) => {
      if (out.at(-1)?.group !== o.group) out.push({ group: o.group, items: [] });
      out.at(-1)!.items.push({ o, i });
    });
    return out;
  }, [shown]);

  const show = () => {
    setTab(initialTab);
    setActive(0);
    setOpen(true);
  };
  const close = () => {
    setOpen(false);
    setQ("");
  };
  const pick = (o: ScopeOption | undefined) => {
    if (!o) return;
    if (o.scope) onPick(o.scope);
    else onClear();
    close();
  };
  const switchTab = (t: ScopeTab) => {
    setTab(t);
    setActive(0);
  };

  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const away = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) close();
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  // "/" opens the search and "p" arms the pin, from anywhere that isn't a text field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || (e.target as HTMLElement | null)?.closest?.("input, textarea")) return;
      if (e.key === "/") {
        e.preventDefault();
        show();
      } else if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        close();
        onPin(!pinArmed);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className={s.scope} ref={root} data-open={open ? "1" : "0"}>
      {pinArmed ? (
        <div className={s.scopePill} data-armed="1" role="status">
          <span className={s.scopeArmed}>Click the map to drop a {RULE_MI}-mile pin</span>
          <button type="button" className={s.scopeX} onClick={() => onPin(false)} aria-label="Cancel pin">Esc</button>
        </div>
      ) : (
        <div className={s.scopePill}>
          <button type="button" className={s.scopeOpen} onClick={() => (open ? close() : show())}
            aria-expanded={open} aria-controls={`${id}-list`} aria-label={`Scope: ${current ?? "United States"}. Change scope`}>
            <span className={s.scopeKicker}>Scope</span>
            <span className={s.scopeName}>{current ?? "United States"}</span>
            <span className={s.scopeCount} aria-live="polite">
              {current ? <>{count.toLocaleString("en-US")}<span> of {total.toLocaleString("en-US")}</span></> : total.toLocaleString("en-US")}
            </span>
            {current ? null : <span className={s.scopeCaret} aria-hidden>/</span>}
          </button>
          {current ? <button type="button" className={s.scopeX} onClick={onClear} aria-label="Back to the United States">×</button> : null}
        </div>
      )}
      <button type="button" className={s.scopePinBtn} aria-pressed={pinArmed}
        onClick={() => {
          close();
          onPin(!pinArmed);
        }}
        title={`Drop a pin: everything within ${RULE_MI} mi (P)`} aria-label={`Drop a pin: everything within ${RULE_MI} miles`}>
        <i className={s.scopeGlyph} aria-hidden />
      </button>
      {open ? (
        <div className={s.scopePanel}>
          <input
            ref={input}
            type="search"
            role="combobox"
            aria-expanded
            aria-controls={`${id}-list`}
            aria-activedescendant={shown.length ? `${id}-${active}` : undefined}
            aria-label="Search states, regions and grid plans"
            placeholder="State, region or grid plan"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            onKeyDown={(e) => {
              if ((e.key === "ArrowDown" || e.key === "ArrowUp") && shown.length) {
                e.preventDefault();
                setActive((a) => (a + (e.key === "ArrowDown" ? 1 : shown.length - 1)) % shown.length);
              } else if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && !q) {
                e.preventDefault();
                switchTab(tab === "places" ? "grid" : "places");
              } else if (e.key === "Enter") {
                e.preventDefault();
                pick(shown[active]);
              } else if (e.key === "Escape") {
                e.stopPropagation();
                close();
              }
            }}
          />
          {q ? null : (
            <div className={s.scopeTabs} role="tablist" aria-label="Scope kind">
              {TABS.map((t) => (
                <button key={t.tab} type="button" role="tab" aria-selected={tab === t.tab} tabIndex={-1}
                  onClick={() => {
                    switchTab(t.tab);
                    input.current?.focus();
                  }}>
                  {t.label}
                </button>
              ))}
            </div>
          )}
          <ul className={s.scopeList} role="listbox" id={`${id}-list`} aria-label="Scopes">
            {runs.map(({ group, items }) => {
              const rows = items.map(({ o, i }) => (
                <li key={`${o.group}:${o.label}`} role="none">
                  <button type="button" role="option" id={`${id}-${i}`} aria-selected={i === active} tabIndex={-1}
                    onMouseEnter={() => setActive(i)} onClick={() => pick(o)} style={{ ["--share" as string]: o.count / max }}>
                    <span>{o.label}</span>
                    <b>{o.count.toLocaleString("en-US")}</b>
                  </button>
                </li>
              ));
              return [
                group ? <li key={`h:${group}`} className={s.scopeGroup} role="presentation">{group}</li> : null,
                // States read down two columns, so ↓ and the eye both go A–Z.
                group === "States"
                  ? <li key="cols" role="none"><ul className={s.scopeCols} role="group" aria-label="States">{rows}</ul></li>
                  : rows,
              ];
            })}
            {shown.length === 0 ? <li className={s.scopeNone} role="none">No state, region or grid plan matches “{q}”.</li> : null}
            {!q && tab === "grid" && unplanned ? (
              <li className={s.scopeNone} role="none">
                {unplanned.toLocaleString("en-US")} drawn projects have no grid plan on file. Find them under Places.
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
