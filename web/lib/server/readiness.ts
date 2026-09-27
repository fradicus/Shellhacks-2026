// Per-capability readiness for /api/health. Each capability says whether it can serve and which published release it
// serves; providers say only whether they are configured. No connection strings, keys or raw errors ever appear.

export type DbState = "up" | "down" | "not_configured";

export interface ProbeResult {
  db: DbState;
  legacy_release: string | null;
  national_release: string | null;
}

export interface ProviderReadiness {
  id: string;
  ready: boolean;
  reason: string | null;
}

export interface Capabilities {
  legacy_dataset: { ready: boolean; release: string | null; reason: string | null };
  national_dataset: { ready: boolean; mode: "atlas" | "snapshot"; release: string | null; reason: string | null };
  verified_artifacts: { ready: boolean; dataset: string | null; generated_at: string | null };
  providers: ProviderReadiness[];
}

const dbReason = (db: DbState) => (db === "not_configured" ? "database not configured" : db === "down" ? "database unreachable" : null);

export function capabilities(input: {
  probe: ProbeResult;
  national_snapshot: { enabled: boolean; ready: boolean; release: string | null };
  verified: { ready: boolean; dataset: string | null; generated_at: string | null };
  providers: ProviderReadiness[] | null;
}): Capabilities {
  const { probe } = input;
  const legacyReason = dbReason(probe.db) ?? (probe.legacy_release ? null : "no active legacy release");
  const national = input.national_snapshot.enabled
    ? { ready: input.national_snapshot.ready, mode: "snapshot" as const, release: input.national_snapshot.release,
        reason: input.national_snapshot.ready ? null : "committed national snapshot failed validation" }
    : { ready: probe.db === "up" && !!probe.national_release, mode: "atlas" as const, release: probe.national_release,
        reason: dbReason(probe.db) ?? (probe.national_release ? null : "no active national release") };
  return {
    legacy_dataset: { ready: !legacyReason, release: probe.legacy_release, reason: legacyReason },
    national_dataset: national,
    verified_artifacts: input.verified,
    providers: input.providers ?? [{ id: "operations", ready: false, reason: "provider readiness could not be read" }],
  };
}
