"use client";

import { useEffect, useState } from "react";
import type { CandidateError, CandidatePage } from "@/lib/national-pairs/types";

/** Pages belong to one dataset and scope. Aborted requests cannot replace a newer scope. */
export function useCandidatePairs(dataset: string | null, scope: string | null, enabled: boolean, sharedId: string | null, query: string) {
  const key = JSON.stringify([dataset, scope, enabled, sharedId, query]);
  const [cursor, setCursor] = useState({ key: "", offset: 0 });
  const [attempt, setAttempt] = useState(0);
  const offset = cursor.key === key ? cursor.offset : 0;
  const request = JSON.stringify([key, offset, attempt]);
  const [result, setResult] = useState<{
    key: string; request: string; page?: CandidatePage; shared?: CandidatePage; error?: string; refresh?: boolean;
  }>({ key: "", request: "" });
  useEffect(() => {
    if (!enabled || !dataset) return;
    const controller = new AbortController();
    async function get(params: URLSearchParams) {
      const response = await fetch(`/api/national-pairs?${params}`, { signal: controller.signal, cache: "no-store" });
      const body: CandidatePage | CandidateError = await response.json();
      if (!response.ok || !body.available) {
        throw Object.assign(new Error(!body.available ? body.reason : "Candidate list unavailable."), { refresh: response.status === 409 });
      }
      if (body.dataset !== dataset) throw Object.assign(new Error("Dataset changed. Refresh the page."), { refresh: true });
      return body;
    }
    const params = new URLSearchParams({ dataset, offset: String(offset) });
    if (scope) params.set("scope", scope);
    if (query) params.set("q", query);
    Promise.all([
      get(params),
      offset === 0 && sharedId ? get(new URLSearchParams({ dataset, id: sharedId })) : Promise.resolve(undefined),
    ]).then(([page, shared]) => {
      if (controller.signal.aborted) return;
      setResult((old) => ({ key, request, shared: shared ?? (old.key === key ? old.shared : undefined),
        page: offset > 0 && old.key === key && old.page ? { ...page,
          pairs: [...new Map([...old.page.pairs, ...page.pairs].map((p) => [p.id, p])).values()],
          projects: [...new Map([...old.page.projects, ...page.projects].map((p) => [p._id, p])).values()],
        } : page }));
    }).catch((error: Error & { refresh?: boolean }) => {
      if (!controller.signal.aborted) setResult((old) => ({ ...(old.key === key ? old : {}), key, request,
        error: error.message || "Candidate list unavailable.", refresh: error.refresh }));
    });
    return () => controller.abort();
  }, [dataset, scope, enabled, sharedId, query, key, offset, request]);
  const current = result.key === key ? result : undefined;
  return {
    page: current?.page, shared: current?.shared,
    loading: enabled && !!dataset && current?.request !== request,
    error: enabled && !dataset ? "National dataset unavailable." : current?.error,
    refresh: current?.refresh,
    reset: () => setCursor({ key, offset: 0 }),
    retry: () => setAttempt((n) => n + 1),
    loadMore: () => { if (current?.page?.nextOffset != null) setCursor({ key, offset: current.page.nextOffset }); },
  };
}
