"use client";

import Link from "next/link";
import { useState } from "react";
import styles from "./search.module.css";

interface Hit {
  id: string;
  kind: "match" | "project" | "brief";
  ref_id: string;
  text: string;
  score?: number;
  rank?: number;
}

interface SearchResponse {
  mode?: "search" | "neighbors";
  results?: Hit[];
  unavailable?: boolean;
  reason?: string;
  error?: string;
}

const KIND_LABEL: Record<Hit["kind"], string> = { match: "Pair", project: "Project", brief: "Brief" };

export function SearchBox() {
  const [input, setInput] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "done" | "failed">("idle");
  const [resp, setResp] = useState<SearchResponse | null>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    const value = input.trim();
    if (!value) return;
    setState("loading");
    setResp(null);
    const param = value.includes("__") ? `ref_id=${encodeURIComponent(value)}` : `q=${encodeURIComponent(value)}`;
    try {
      const res = await fetch(`/api/search?${param}`);
      const body = (await res.json()) as SearchResponse;
      setResp(body);
      setState(res.ok ? "done" : "failed");
    } catch {
      setResp(null);
      setState("failed");
    }
  }

  return (
    <section className={styles.box}>
      <form onSubmit={run} className={styles.form}>
        <input
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Plain-language question, or a pair id like DESC:6808 S__GPC:20067"
          aria-label="Semantic search query"
        />
        <button className={styles.button} type="submit" disabled={state === "loading"}>
          {state === "loading" ? "Searching…" : "Search"}
        </button>
      </form>

      {state === "failed" && (
        <p className={styles.note} role="status">
          {resp?.unavailable
            ? `Search is unavailable (${resp.reason ?? "database not configured"}).`
            : (resp?.error ?? "Search failed; try again.")}
        </p>
      )}
      {state === "done" && resp?.results && resp.results.length === 0 && (
        <p className={styles.note} role="status">
          No results. Embeddings load with the next data push that includes them.
        </p>
      )}

      {state === "done" && resp?.results && resp.results.length > 0 && (
        <ol className={styles.results}>
          {resp.results.map((hit) => (
            <li key={`${hit.id}-${hit.rank ?? hit.score ?? 0}`} className={styles.hit}>
              <div className={styles.hitHead}>
                <span className={styles.badge} data-kind={hit.kind}>
                  {KIND_LABEL[hit.kind]}
                </span>
                <code className={styles.ref}>{hit.ref_id}</code>
                {typeof hit.score === "number" && <span className={styles.score}>{hit.score.toFixed(3)}</span>}
                {hit.kind === "match" && <Link href={`/pair/${encodeURIComponent(hit.ref_id)}`}>Open pair</Link>}
              </div>
              <p className={styles.text}>{hit.text}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
