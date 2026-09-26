"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  APPROVED_VIEWS, parseOfflineCommand, validateAssistantAction,
  type AssistantAction, type AssistantContext,
} from "@/lib/assistant/commands";
import styles from "./assistant.module.css";

// Structural subset of F31's controller: the optional branch cannot acquire wider app privileges.
export interface AssistantController {
  results: Readonly<{ ids: readonly string[]; total: number; located: number; unlocated: number }>;
  availability: Readonly<{ loading: boolean; available: boolean; mode: string }>;
  reference: Readonly<{
    states: AssistantContext["states"];
    counties: AssistantContext["counties"];
    regions: AssistantContext["regions"];
    sources: ReadonlyArray<{ planning_region: string | null }>;
  }>;
  applyAction(action: Exclude<AssistantAction, { type: "navigate" }>): { ok: boolean; reason?: string };
  reset(): void;
  undo(): { ok: boolean; reason?: string };
}

const EXAMPLES = ["show projects in Massachusetts", "show planned projects in Connecticut", "focus Alaska"];

export function AssistantPanel({ controller }: { controller: AssistantController }) {
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [feedback, setFeedback] = useState("Try a supported command. This preview does not use a language model.");
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const router = useRouter();
  const { loading, available, mode } = controller.availability;

  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);

  function close() {
    setOpen(false);
    toggle.current?.focus();
  }

  function run(command: string) {
    const context: AssistantContext = {
      ...controller.reference,
      planningRegions: [...new Set(controller.reference.sources.flatMap((source) => source.planning_region ? [source.planning_region] : []))],
      owners: [], // Owner inference is deliberately outside this first offline command grammar.
      visibleProjectIds: loading || !available ? [] : controller.results.ids,
    };
    const answer = parseOfflineCommand(command, context);
    if (!answer.ok) {
      setFeedback(answer.message);
      return;
    }
    try {
      const action = validateAssistantAction(answer.action, context);
      if (action.type === "navigate") {
        setFeedback(answer.summary);
        router.push(APPROVED_VIEWS[action.view]);
        return;
      }
      const applied = controller.applyAction(action);
      if (!applied.ok) {
        setFeedback(applied.reason ?? "This action could not be applied to the current view.");
        return;
      }
      setLastCommand(command);
      setFeedback(answer.summary);
      setPrompt("");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "The requested action is no longer available.");
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    run(prompt);
  }

  return (
    <>
      <button ref={toggle} type="button" className={styles.toggle} aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
        <span aria-hidden="true">✦</span> Ask the grid <span className={styles.tag}>Preview</span>
      </button>
      {open ? (
        <aside id={panelId} aria-label="App control preview" className={styles.panel} onKeyDown={(event) => {
          if (event.key === "Escape") { event.stopPropagation(); close(); }
        }}>
          <header className={styles.header}>
            <div><p className={styles.eyebrow}>App control preview</p><h2>Ask the grid</h2></div>
            <button type="button" onClick={close} aria-label="Close app control preview" className={styles.close}>×</button>
          </header>
          <p className={styles.notice}><strong>Offline commands.</strong> A language model is not connected. This preview can change filters, focus the map, and select a visible project.</p>
          <div className={styles.examples} aria-label="Example commands">
            {EXAMPLES.map((example) => <button type="button" key={example} onClick={() => { setPrompt(example); input.current?.focus(); }}>{example}</button>)}
          </div>
          <form onSubmit={submit} className={styles.form}>
            <label htmlFor={`${panelId}-prompt`}>What would you like to see?</label>
            <textarea ref={input} id={`${panelId}-prompt`} value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={500} rows={3}
              placeholder="Show projects in Massachusetts" />
            <button type="submit" disabled={!prompt.trim()} className={styles.submit}>Apply command <span aria-hidden="true">→</span></button>
          </form>
          <p role="status" aria-live="polite" className={styles.feedback}>{feedback}</p>
          <div className={styles.current}>
            <span className={styles.eyebrow}>Current explorer view</span>
            {loading ? <p>Updating results…</p> : !available ? <p>Project data is unavailable. No count is being claimed.</p> : (
              <p><strong>{controller.results.total.toLocaleString("en-US")}</strong> matching imported records · {controller.results.located.toLocaleString("en-US")} with coordinates · {controller.results.unlocated.toLocaleString("en-US")} unlocated</p>
            )}
            <small>{mode === "snapshot" ? "Published local snapshot; this is not live Atlas." : "Imported records do not represent complete US project coverage."}</small>
          </div>
          <div className={styles.actions}>
            <button type="button" onClick={() => {
              const changed = controller.undo();
              setFeedback(changed.ok ? "Restored the previous explorer state." : changed.reason ?? "There is no earlier change to restore.");
            }}>Undo last change</button>
            <button type="button" onClick={() => { controller.reset(); setFeedback("Reset all project filters."); }}>Reset filters</button>
          </div>
          {lastCommand ? <p className={styles.last}>Last applied: {lastCommand}</p> : null}
          <p className={styles.footer}>Commands change this view. They cannot edit project data or invent locations, dates, or savings.</p>
        </aside>
      ) : null}
    </>
  );
}
