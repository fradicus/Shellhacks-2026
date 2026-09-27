// Operations route failures by cause, so a caller can tell its own mistake from a provider outage, a missing
// configuration, a timeout or a bad published artifact. Messages are fixed strings: no provider text, no secrets.
import { ZodError } from "zod";

export const FAILURES = {
  invalid_input: { status: 400, error: "Invalid request" },
  body_too_large: { status: 413, error: "Request body too large" },
  departure_window: { status: 422, error: "Departure must be now through seven days ahead" },
  not_configured: { status: 503, error: "A required provider is not configured" },
  publication_failure: { status: 503, error: "A published operations artifact failed validation" },
  provider_failure: { status: 502, error: "An upstream provider failed" },
  timeout: { status: 504, error: "The request timed out" },
  internal: { status: 500, error: "Operations request failed" },
} as const;
export type FailureCode = keyof typeof FAILURES;

export class OperationsError extends Error {
  readonly code: FailureCode;
  constructor(code: FailureCode, message: string = FAILURES[code].error) {
    super(message);
    this.name = "OperationsError";
    this.code = code;
  }
}

/** An error raised while reading the request: always the caller's input, except a body that took too long. */
export function inputFailure(error: unknown): FailureCode {
  if (error instanceof OperationsError) return error.code;
  if (error instanceof Error && /deadline/i.test(error.message)) return "timeout";
  return "invalid_input";
}

/** An error raised after the request parsed: classified by what failed, never blamed on the caller by default. */
export function serviceFailure(error: unknown): FailureCode {
  if (error instanceof OperationsError) return error.code;
  if (error instanceof ZodError) return "provider_failure";
  if (error instanceof Error) {
    if (error.name === "TimeoutError" || error.name === "AbortError" || /deadline exceeded|timed out/i.test(error.message)) return "timeout";
    if (/fetch failed|ECONN|ENOTFOUND|EAI_AGAIN|socket/i.test(error.message)) return "provider_failure";
  }
  return "internal";
}

export function failureResponse(code: FailureCode, detail?: string): Response {
  const { status, error } = FAILURES[code];
  return Response.json({ error: detail ?? error, code }, { status, headers: { "Cache-Control": "no-store" } });
}
