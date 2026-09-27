"use client";

import { useEffect, useState, type ReactNode } from "react";
import type { NationalProjectDetail } from "@/lib/national/types";

type Detail = Extract<NationalProjectDetail, { available: true }>;

/** Only mount for the selected record or an opened evidence disclosure. */
export function ProjectDetail({ id, dataset, children }: {
  id: string; dataset: string | null; children(detail: Detail): ReactNode;
}) {
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([id, dataset, attempt]);
  const [result, setResult] = useState<{ key: string; detail?: Detail; error?: string; refresh?: boolean } | null>(null);
  useEffect(() => {
    if (!dataset) return;
    const abort = new AbortController();
    const query = new URLSearchParams({ id, dataset });
    fetch(`/api/national/project?${query}`, { signal: abort.signal, cache: "no-store" })
      .then(async (response) => {
        const body = await response.json() as NationalProjectDetail;
        if (abort.signal.aborted) return;
        if (!response.ok || !body.available) {
          setResult({ key, error: !body.available ? body.reason : "Project evidence is unavailable.", refresh: response.status === 409 });
        } else if (body.dataset !== dataset || body.project._id !== id) {
          setResult({ key, error: "Evidence did not match the selected project. Please retry." });
        } else setResult({ key, detail: body });
      })
      .catch(() => { if (!abort.signal.aborted) setResult({ key, error: "Project evidence could not be loaded. Please retry." }); });
    return () => abort.abort();
  }, [id, dataset, key]);
  if (!dataset) return <p role="alert">Project evidence is unavailable without a published dataset.</p>;
  if (result?.key !== key) return <p role="status">Loading project evidence…</p>;
  if (result.error) return <div role="alert"><p>{result.error}</p>
    {result.refresh ? <button type="button" onClick={() => window.location.reload()}>Refresh page</button>
      : <button type="button" onClick={() => setAttempt((value) => value + 1)}>Retry evidence</button>}
  </div>;
  return result.detail ? children(result.detail) : null;
}
