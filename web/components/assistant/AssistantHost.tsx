"use client";

import { createContext, useCallback, useContext, useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AssistantActionSchema, buildAssistantHref, validateAssistantAction, type AssistantAction, type AssistantContext } from "@/lib/assistant/commands";
import type { AssistantResponse, AssistantStatus } from "@/lib/assistant/contracts";
import type { NationalExplorerController, NationalFilters } from "@/lib/national/types";
import styles from "./assistant.module.css";

export interface AssistantRegistration {
  controller: NationalExplorerController;
  planningRegions: readonly string[];
  owners: readonly string[];
  dataset: string | null;
}
interface HostContextValue { register(value: AssistantRegistration): () => void }
const HostContext = createContext<HostContextValue | null>(null);
const EMPTY_FILTERS: NationalFilters = { page: 1, limit: 25 };
const EXAMPLES = ["Show projects in Florida", "Focus Georgia", "Open field planning"];
type Message = { id: number; role: "user" | "assistant" | "system"; text: string };
type RequestState = { abort: AbortController; signature: string; prompt: string };
type UndoTarget = { kind: "controller" } | { kind: "route"; href: string };

function statusPayload(value: unknown): AssistantStatus {
  if (!value || typeof value !== "object") throw new Error("Assistant status was malformed.");
  const item = value as Record<string, unknown>;
  if (typeof item.ready !== "boolean" || (item.mode !== "gemini" && item.mode !== "unavailable")
    || !(item.reason === null || typeof item.reason === "string") || !(item.model === null || typeof item.model === "string")
    || item.ready !== (item.mode === "gemini") || (item.ready && !item.model)) throw new Error("Assistant status was malformed or inconsistent.");
  return item as AssistantStatus;
}

function responsePayload(value: unknown, requestId: string, dataset: string | null): AssistantResponse {
  if (!value || typeof value !== "object") throw new Error("Assistant reply was malformed.");
  const item = value as Record<string, unknown>;
  const statuses = ["action", "clarification", "answer", "unsupported", "unavailable"];
  if (!statuses.includes(String(item.status)) || typeof item.message !== "string" || item.message.length > 2000
    || item.requestId !== requestId || !(item.model === null || typeof item.model === "string")
    || !(item.provider === null || item.provider === "gemini") || !(item.action === null || typeof item.action === "object")
    || !(item.dataset === null || typeof item.dataset === "string") || item.dataset !== dataset
    || ((item.status === "action") !== (item.action !== null))
    || (item.provider === "gemini") !== (typeof item.model === "string")
    || (["action", "answer", "unsupported"].includes(String(item.status)) && item.provider !== "gemini")
    || (item.provider === null && !["clarification", "unavailable"].includes(String(item.status)))) {
    throw new Error("Assistant reply was malformed or belonged to another request.");
  }
  return item as AssistantResponse;
}

function assistantContext(value: AssistantRegistration): AssistantContext {
  const { controller } = value;
  return {
    states: controller.reference.states,
    counties: controller.reference.counties,
    regions: controller.reference.regions,
    planningRegions: value.planningRegions,
    owners: value.owners,
    visibleProjectIds: controller.availability.loading || !controller.availability.available ? [] : controller.results.ids.slice(0, 100),
  };
}
function filterSignature(filters: Readonly<NationalFilters>): string { return JSON.stringify(filters, Object.keys(filters).sort()); }
function currentSafeHref(pathname: string): string | null {
  // usePathname supplies only this app's path; reject URL-like or Windows separators before retaining it for one undo.
  if (!pathname.startsWith("/") || pathname.startsWith("//") || pathname.includes("\\") || /[\u0000-\u001f]/.test(pathname)) return null;
  return `${pathname}${typeof window === "undefined" ? "" : window.location.search}`;
}
export function useAssistantHost(): HostContextValue | null { return useContext(HostContext); }

export function AssistantHost({ children }: { children: ReactNode }) {
  const [registration, setRegistration] = useState<AssistantRegistration | null>(null);
  const registrationToken = useRef<symbol | null>(null);
  const register = useCallback((value: AssistantRegistration) => {
    const token = Symbol("assistant-registration"); registrationToken.current = token; setRegistration(value);
    return () => { if (registrationToken.current === token) { registrationToken.current = null; setRegistration(null); } };
  }, []);
  const context = useMemo(() => ({ register }), [register]);
  return <HostContext.Provider value={context}>{children}<AssistantPanel registration={registration} /></HostContext.Provider>;
}

function AssistantPanel({ registration }: { registration: AssistantRegistration | null }) {
  const router = useRouter(); const pathname = usePathname(); const panelId = useId(); const headingId = `${panelId}-heading`;
  const input = useRef<HTMLTextAreaElement>(null); const toggle = useRef<HTMLButtonElement>(null); const active = useRef<RequestState | null>(null);
  const statusAbort = useRef<AbortController | null>(null);
  const messageId = useRef(0); const [open, setOpen] = useState(false); const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([]); const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true); const [statusError, setStatusError] = useState<string | null>(null);
  const [request, setRequest] = useState<RequestState | null>(null); const [requestError, setRequestError] = useState<string | null>(null);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null); const [undoTarget, setUndoTarget] = useState<UndoTarget | null>(null);
  const [awaitingCount, setAwaitingCount] = useState<string | null>(null); const controller = registration?.controller ?? null;
  const filters = controller?.filters ?? EMPTY_FILTERS; const signature = `${pathname}|${filterSignature(filters)}|${controller?.selectedProjectId ?? ""}`;
  const contextSignature = `${signature}|${registration?.dataset ?? ""}|${controller?.availability.loading ?? false}|${controller?.availability.available ?? false}`;
  const latestSignature = useRef(contextSignature);
  const addMessage = useCallback((role: Message["role"], text: string) => setMessages((items) => [...items, { id: ++messageId.current, role, text }]), []);

  const loadStatus = useCallback(async () => {
    statusAbort.current?.abort(); const abort = new AbortController(); statusAbort.current = abort;
    setStatusLoading(true); setStatusError(null);
    try {
      const response = await fetch("/api/assistant", { cache: "no-store", signal: abort.signal, headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("Assistant readiness could not be checked.");
      setStatus(statusPayload(await response.json().catch(() => null)));
    } catch { if (!abort.signal.aborted) { setStatus(null); setStatusError("Assistant readiness could not be checked."); } }
    finally { if (statusAbort.current === abort) { statusAbort.current = null; setStatusLoading(false); } }
  }, []);
  useLayoutEffect(() => { latestSignature.current = contextSignature; }, [contextSignature]);
  useEffect(() => { const timer = setTimeout(() => void loadStatus(), 0); return () => clearTimeout(timer); }, [loadStatus]);
  useEffect(() => () => { active.current?.abort.abort(); statusAbort.current?.abort(); }, []);
  useEffect(() => {
    const running = active.current;
    if (!running || running.signature === contextSignature) return;
    running.abort.abort(); active.current = null; setRequest(null); addMessage("system", "The view changed, so the pending reply was cancelled before it could act.");
  }, [addMessage, contextSignature]);
  useEffect(() => {
    if (!awaitingCount || !controller || controller.availability.loading) return;
    const current = filterSignature(controller.filters); if (current === awaitingCount) return;
    const timer = setTimeout(() => {
      addMessage("system", controller.availability.available
        ? `${controller.results.total.toLocaleString("en-US")} matching imported records are now loaded; ${controller.results.located.toLocaleString("en-US")} have displayed coordinates.`
        : "The project result set is unavailable, so no count is claimed.");
      setAwaitingCount(null);
    }, 0);
    return () => clearTimeout(timer);
  }, [addMessage, awaitingCount, controller]);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);

  function close() { setOpen(false); requestAnimationFrame(() => toggle.current?.focus()); }
  function cancel() { const running = active.current; if (!running) return; running.abort.abort(); active.current = null; setRequest(null); addMessage("system", "Request cancelled."); }
  function execute(actionValue: unknown): { ok: boolean; reason?: string } {
    if (registration) {
      let action: AssistantAction;
      try { action = validateAssistantAction(actionValue, assistantContext(registration)); }
      catch (error) { return { ok: false, reason: error instanceof Error ? error.message : "The action is no longer valid." }; }
      if (action.type !== "navigate") {
        if (action.type !== "filters.reset" && (registration.controller.availability.loading || !registration.controller.availability.available)) return { ok: false, reason: "Wait for the current project results before applying that action." };
        const before = filterSignature(registration.controller.filters); const result = registration.controller.applyAction(action);
        if (result.ok) { setUndoTarget({ kind: "controller" }); if (action.type.startsWith("filters.")) setAwaitingCount(before); }
        return result;
      }
      const href = buildAssistantHref(action, registration.controller.filters); if (!href) return { ok: false, reason: "That destination is not available." };
      const previous = currentSafeHref(pathname); setUndoTarget(previous ? { kind: "route", href: previous } : null); router.push(href); return { ok: true };
    }
    let href: string | null;
    try { href = buildAssistantHref(AssistantActionSchema.parse(actionValue), filters); }
    catch (error) { return { ok: false, reason: error instanceof Error ? error.message : "That action is not supported." }; }
    if (!href) return { ok: false, reason: "Open the explorer before selecting a project or changing the map focus." };
    const previous = currentSafeHref(pathname); setUndoTarget(previous ? { kind: "route", href: previous } : null); router.push(href); return { ok: true };
  }

  async function ask(text: string) {
    const message = text.trim(); if (!message || message.length > 1000 || request) return;
    if (!status?.ready) { setRequestError(status?.reason ?? statusError ?? "Gemini is unavailable."); return; }
    const requestId = `web-${Date.now().toString(36)}-${crypto.randomUUID().slice(0, 20)}`; const abort = new AbortController();
    const dataset = registration?.dataset ?? null;
    const running: RequestState = { abort, signature: contextSignature, prompt: message }; active.current = running; setRequest(running); setRequestError(null); setLastPrompt(message);
    addMessage("user", message); setPrompt("");
    try {
      const response = await fetch("/api/assistant", { method: "POST", cache: "no-store", signal: abort.signal, headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ message, filters, dataset, visibleProjectIds: registration ? assistantContext(registration).visibleProjectIds : [], requestId }) });
      if (!response.ok) {
        if (response.status === 429) throw new Error("The assistant request limit was reached. Please try again shortly.");
        if (response.status === 409) throw new Error("The published dataset changed. Refresh before asking again.");
        throw new Error("The assistant is temporarily unavailable. Please try again.");
      }
      const answer = responsePayload(await response.json().catch(() => null), requestId, dataset);
      if (active.current !== running || abort.signal.aborted || running.signature !== latestSignature.current) return;
      active.current = null; setRequest(null); addMessage(answer.provider === "gemini" ? "assistant" : "system", answer.message);
      if (answer.status === "action") { const result = execute(answer.action); addMessage("system", result.ok ? "Action applied through the current app controls." : `No action was applied: ${result.reason ?? "the action is no longer valid."}`); }
      else if (answer.status === "unavailable") setRequestError(answer.message);
    } catch (error) {
      if (abort.signal.aborted) return;
      if (active.current === running) { active.current = null; setRequest(null); }
      const known = error instanceof Error && [
        "The assistant request limit was reached. Please try again shortly.",
        "The published dataset changed. Refresh before asking again.",
        "The assistant is temporarily unavailable. Please try again.",
      ].includes(error.message);
      setRequestError(known ? (error as Error).message : "Gemini could not answer this request. Please try again.");
    }
  }
  function submit(event: FormEvent) { event.preventDefault(); void ask(prompt); }
  function undo() {
    if (!undoTarget) { addMessage("system", "There is no assistant action to undo."); return; }
    if (undoTarget.kind === "route") router.push(undoTarget.href);
    else { const result = registration?.controller.undo(); if (!result?.ok) { addMessage("system", result?.reason ?? "The prior explorer action is no longer available."); return; } }
    setUndoTarget(null); addMessage("system", "The last assistant action was undone.");
  }

  return <>
    <button ref={toggle} type="button" className={styles.toggle} aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((value) => !value)}><span aria-hidden="true" className={styles.spark}>✦</span><span>Ask Common Ground</span></button>
    {open ? <section id={panelId} role="dialog" aria-modal="false" aria-labelledby={headingId} className={styles.panel} onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <header className={styles.header}><div><p className={styles.eyebrow}>Bounded app assistant</p><h2 id={headingId}>Common Ground</h2></div><button type="button" onClick={close} aria-label="Close Common Ground assistant" className={styles.close}>×</button></header>
      <div className={styles.provider} aria-live="polite"><span className={status?.ready ? styles.readyDot : styles.offDot} aria-hidden="true" />
        {statusLoading ? <span>Checking Gemini readiness…</span> : status?.ready ? <span>Gemini ready · {status.model}</span> : <span>{statusError ?? "Assistant isn’t enabled on this deployment yet."}</span>}
        {!statusLoading && (!status || !status.ready) ? <button type="button" onClick={() => void loadStatus()}>Retry status</button> : null}</div>
      <div className={styles.examples} aria-label="Example requests">{EXAMPLES.map((example) => <button type="button" key={example} onClick={() => { setPrompt(example); input.current?.focus(); }}>{example}</button>)}</div>
      <div className={styles.chat} aria-label="Assistant conversation" aria-live="polite">{messages.length ? messages.map((item) => <article key={item.id} className={styles[item.role]}><span>{item.role === "user" ? "You" : item.role === "assistant" ? "Gemini" : "Common Ground"}</span><p>{item.text}</p></article>)
        : <p className={styles.empty}>Ask for a supported filter, project selection, map focus, approved page, or help with the evidence shown in Common Ground.</p>}</div>
      <form onSubmit={submit} className={styles.form}><label htmlFor={`${panelId}-prompt`}>Ask Common Ground</label><textarea ref={input} id={`${panelId}-prompt`} value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={1000} rows={3} placeholder="Show projects in Florida" disabled={!status?.ready || !!request} />
        <div className={styles.formActions}>{request ? <button type="button" onClick={cancel} className={styles.secondary}>Cancel</button> : <button type="submit" disabled={!status?.ready || !prompt.trim()} className={styles.submit}>Ask Gemini <span aria-hidden="true">→</span></button>}</div></form>
      {request ? <p className={styles.progress} role="status">Gemini is preparing a bounded response…</p> : null}
      {requestError ? <div className={styles.error} role="alert"><p>{requestError}</p>{lastPrompt && status?.ready ? <button type="button" onClick={() => void ask(lastPrompt)}>Retry request</button> : null}</div> : null}
      <section className={styles.current} aria-label="Current explorer result state"><span className={styles.eyebrow}>Current imported records</span>
        {!controller ? <p>Open the national explorer to show a verified result count. Global navigation and filters will route there.</p> : controller.availability.loading ? <p>Updating results…</p> : !controller.availability.available ? <p>Project data is unavailable. No count is claimed.</p> : <p><strong>{controller.results.total.toLocaleString("en-US")}</strong> matches · {controller.results.located.toLocaleString("en-US")} with displayed coordinates · {controller.results.unlocated.toLocaleString("en-US")} unlocated</p>}
        {registration?.dataset ? <small>Dataset {registration.dataset}</small> : null}</section>
      <div className={styles.actions}><button type="button" onClick={undo} disabled={!undoTarget}>Undo assistant action</button><button type="button" onClick={() => {
        if (registration) { registration.controller.reset(); setUndoTarget({ kind: "controller" }); }
        else { const previous = currentSafeHref(pathname); setUndoTarget(previous ? { kind: "route", href: previous } : null); router.push("/assistant"); }
      }}>Reset explorer filters</button></div>
      <p className={styles.footer}>Common Ground can operate approved controls and explain bounded evidence. It cannot write data, run code, open arbitrary URLs, invent locations or promise savings.</p>
    </section> : null}
  </>;
}
