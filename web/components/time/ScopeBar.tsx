"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { RULE_MI, type Scope } from "./scope";
import s from "./time.module.css";

export interface ScopeOption { group: "Regions" | "Grid plans" | "States"; scope: Scope; label: string; hint?: string; count: number }

/** One control for "which part of the map" (F19 spec 15): a search over regions, grid plans and states, plus a pin. */
export function ScopeBar({ current, count, total, options, pinArmed, onPick, onClear, onPin }: {
  current: string | null;
  count: number;
  total: number;
  options: ScopeOption[];
  pinArmed: boolean;
  onPick(scope: Scope): void;
  onClear(): void;
  onPin(armed: boolean): void;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();

  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    return t ? options.filter((o) => o.label.toLowerCase().includes(t) || o.hint?.toLowerCase() === t) : options;
  }, [options, q]);
  // The pin is the last row, so ↓ past the states reaches it.
  const rows = shown.length + 1;
  const max = Math.max(...options.map((o) => o.count), 1);

  const close = () => {
    setOpen(false);
    setQ("");
  };
  const pick = (i: number) => {
    if (i === shown.length) onPin(true);
    else if (shown[i]) onPick(shown[i].scope);
    close();
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

  // "/" opens the search from anywhere that isn't a text field.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || (e.target as HTMLElement | null)?.closest?.("input, textarea")) return;
      e.preventDefault();
      setOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className={s.scope} ref={root} data-open={open ? "1" : "0"}>
      {pinArmed ? (
        <div className={s.scopePill} data-armed="1" role="status">
          <i className={s.scopeGlyph} aria-hidden />
          <span className={s.scopeArmed}>Click the map to drop a {RULE_MI}-mile pin</span>
          <button type="button" className={s.scopeX} onClick={() => onPin(false)} aria-label="Cancel pin">Esc</button>
        </div>
      ) : (
        <div className={s.scopePill}>
          <button type="button" className={s.scopeOpen} onClick={() => (open ? close() : setOpen(true))}
            aria-expanded={open} aria-controls={`${id}-list`} aria-label={`Scope: ${current ?? "All projects"}. Change scope`}>
            <i className={s.scopeGlyph} aria-hidden />
            <span className={s.scopeKicker}>Scope</span>
            <span className={s.scopeName}>{current ?? "All projects"}</span>
            <span className={s.scopeCount} aria-live="polite">
              {current ? <>{count.toLocaleString("en-US")}<span> of {total.toLocaleString("en-US")}</span></> : total.toLocaleString("en-US")}
            </span>
            {current ? null : <span className={s.scopeCaret} aria-hidden>/</span>}
          </button>
          {current ? <button type="button" className={s.scopeX} onClick={onClear} aria-label="Clear scope, show all projects">×</button> : null}
        </div>
      )}
      {open ? (
        <div className={s.scopePanel}>
          <input
            ref={input}
            type="search"
            role="combobox"
            aria-expanded
            aria-controls={`${id}-list`}
            aria-activedescendant={`${id}-${active}`}
            aria-label="Search regions, grid plans and states"
            placeholder="Region, grid plan or state"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setActive(0);
            }}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => (a + (e.key === "ArrowDown" ? 1 : rows - 1)) % rows);
              } else if (e.key === "Enter") {
                e.preventDefault();
                pick(active);
              } else if (e.key === "Escape") {
                e.stopPropagation();
                close();
              }
            }}
          />
          <ul className={s.scopeList} role="listbox" id={`${id}-list`} aria-label="Scopes">
            {shown.map((o, i) => {
              const head = i === 0 || shown[i - 1].group !== o.group ? o.group : null;
              return (
                <li key={`${o.group}:${o.label}`} role="none">
                  {head ? <p className={s.scopeGroup} aria-hidden>{head}</p> : null}
                  <button type="button" role="option" id={`${id}-${i}`} aria-selected={i === active} tabIndex={-1}
                    onMouseEnter={() => setActive(i)} onClick={() => pick(i)} style={{ ["--share" as string]: o.count / max }}>
                    <span>{o.label}</span>
                    {o.hint ? <em>{o.hint}</em> : null}
                    <b>{o.count.toLocaleString("en-US")}</b>
                  </button>
                </li>
              );
            })}
            {shown.length === 0 ? <li className={s.scopeNone} role="none">No region, plan or state matches “{q}”.</li> : null}
            <li role="none">
              <button type="button" role="option" id={`${id}-${shown.length}`} aria-selected={active === shown.length} tabIndex={-1}
                className={s.scopePin} onMouseEnter={() => setActive(shown.length)} onClick={() => pick(shown.length)}>
                <i aria-hidden />
                <span>Drop a pin</span>
                <em>everything within {RULE_MI} mi</em>
              </button>
            </li>
          </ul>
        </div>
      ) : null}
    </div>
  );
}
