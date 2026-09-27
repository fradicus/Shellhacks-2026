import "server-only";

/** A whole request's budget ran out. Distinct from a single query's `maxTimeMS` so callers can say "timed out". */
export class DeadlineExceeded extends Error {
  readonly label: string;
  readonly ms: number;
  constructor(label: string, ms: number) {
    super(`${label} exceeded its ${ms} ms deadline`);
    this.name = "DeadlineExceeded";
    this.label = label;
    this.ms = ms;
  }
}

/** Runs `work` under one total deadline. The signal is aborted when the deadline passes or `parent` aborts (a client
 * that went away), and every query that accepts it is cancelled rather than left running behind a response. */
export async function withDeadline<T>(
  label: string,
  ms: number,
  work: (signal: AbortSignal) => Promise<T>,
  parent?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const expired = new DeadlineExceeded(label, ms);
  const onParent = () => controller.abort(parent?.reason);
  if (parent?.aborted) controller.abort(parent.reason);
  else parent?.addEventListener("abort", onParent, { once: true });
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      controller.abort(expired);
      reject(expired);
    }, ms);
  });
  const aborted = new Promise<never>((_, reject) => {
    if (controller.signal.aborted) reject(controller.signal.reason);
    else controller.signal.addEventListener("abort", () => reject(controller.signal.reason), { once: true });
  });
  // The race settles on the first of work, deadline or abort; the losers are observed so none rejects unhandled.
  deadline.catch(() => undefined);
  aborted.catch(() => undefined);
  try {
    return await Promise.race([work(controller.signal), deadline, aborted]);
  } finally {
    clearTimeout(timer);
    parent?.removeEventListener("abort", onParent);
  }
}
