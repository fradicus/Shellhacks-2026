import { createHash } from "node:crypto";
import { access, open, realpath, stat } from "node:fs/promises";
import { dirname, isAbsolute, join } from "node:path";
import { z } from "zod";

const stamp = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/).refine((s) => {
  const value = Date.parse(s);
  return Number.isFinite(value) && new Date(value).toISOString() === s.replace("Z", ".000Z");
});
const day = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((s) => {
  const value = Date.parse(`${s}T00:00:00Z`);
  return Number.isFinite(value) && new Date(value).toISOString().slice(0, 10) === s;
});
const id = z.string().min(1).max(120).regex(/^[A-Za-z0-9_ .:/-]+$/);
const hash = z.string().regex(/^[0-9a-f]{64}$/);
const positiveDays = z.number().int().min(1).max(3650);
export const PredictRequestSchema = z.object({
  job_type: id, company_id: id, region: id, as_of: stamp,
  planned_duration_days: positiveDays.optional(),
  planned_duration_confirmed_at_as_of: z.literal(true).optional(),
}).strict().superRefine((value, context) => {
  if ((value.planned_duration_days !== undefined) !== (value.planned_duration_confirmed_at_as_of === true)) {
    context.addIssue({ code: "custom", message: "A planned duration requires confirmation it was known at as_of; confirmation requires a baseline." });
  }
});
export type PredictRequest = z.infer<typeof PredictRequestSchema>;
const ObservationSchema = z.object({
  job_id: id, project_lineage: id, component_id: id, job_type: id, company_id: id, region: id,
  decision_at: stamp, features_available_at: stamp, actual_start: day, actual_complete: day, available_at: stamp,
  duration_days: positiveDays, planned_duration_days: positiveDays.nullable(), planned_available_at: stamp.nullable(),
  evidence_hashes: z.array(hash).min(1).max(10),
}).strict();
type Observation = z.infer<typeof ObservationSchema>;
const CutoffsSchema = z.object({ training: stamp, calibration: stamp, evaluation: stamp }).strict();
type Cutoffs = z.infer<typeof CutoffsSchema>;
const intervalSchema = z.object({ lower: z.number().finite(), median: z.number().finite(), upper: z.number().finite() }).strict();
const evaluationSchema = z.object({
  training: z.number().int().nonnegative(), calibration: z.number().int().nonnegative(), holdout: z.number().int().nonnegative(),
  passed: z.boolean(), reasons: z.array(z.string()), interval: intervalSchema.nullable(),
  metrics: z.object({ mae_days: z.number().finite(), baseline_mae_days: z.number().finite(), interval_coverage: z.number().min(0).max(1) }).strict().nullable(),
  probability: z.object({
    passed: z.boolean(), domain: z.object({ lower: positiveDays, upper: positiveDays }).strict(),
    calibration: z.number().int().nonnegative(), holdout: z.number().int().nonnegative(),
    calibration_brier: z.number().min(0).max(1), holdout_brier: z.number().min(0).max(1),
    calibration_baseline_brier: z.number().min(0).max(1), holdout_baseline_brier: z.number().min(0).max(1),
  }).strict().nullable(),
}).strict();
export type Evaluation = z.infer<typeof evaluationSchema>;
const AuditSourceSchema = z.object({
  id, publisher: id, lineage: id, sha256: hash, published_at: stamp, received_at: stamp, reviewed_at: stamp,
  authorization_ref: id, reviewer: id,
}).strict();
const ReviewSchema = z.object({
  job_id: id, decision: z.enum(["accepted", "rejected", "unresolved"]), reviewed_at: stamp, reviewer: id,
  reason: z.string().min(1).max(1000), start_semantics: z.literal("physical_construction_start"),
  completion_semantics: z.literal("physical_construction_complete"),
}).strict();
const ProvenanceSchema = z.object({ import_sha256: hash, sources: z.array(AuditSourceSchema).max(1000), reviews: z.array(ReviewSchema).max(10000) }).strict();
const ArtifactSchema = z.object({
  schema_version: z.literal("outcomes-model-v1"), purpose: z.literal("authorized_actual_history"),
  policy_version: z.literal("empirical-cohort-v1"),
  target: z.literal("physical_construction_start_to_complete_calendar_days"),
  dataset_hash: hash, cutoffs: CutoffsSchema, observations: z.array(ObservationSchema).max(10000),
  provenance: ProvenanceSchema, provenance_hash: hash,
  evaluation: z.record(z.string(), evaluationSchema),
}).strict();
export type Artifact = z.infer<typeof ArtifactSchema>;
const DAY = 86_400_000;
const MAX_BYTES = 16 * 1024 * 1024;
const mean = (xs: number[]) => xs.reduce((sum, x) => sum + x, 0) / xs.length;
function median(xs: number[]) {
  const ordered = [...xs].sort((a, b) => a - b), n = ordered.length;
  return n % 2 ? ordered[Math.floor(n / 2)] : (ordered[n / 2 - 1] + ordered[n / 2]) / 2;
}
const cohort = (row: Pick<Observation, "job_type" | "company_id" | "region">) => JSON.stringify([row.job_type, row.company_id, row.region]);
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${canonical(object[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
const sha256 = (bytes: string | Buffer) => createHash("sha256").update(bytes).digest("hex");

function split(rows: Observation[], cutoffs: Cutoffs): [Observation[], Observation[], Observation[]] {
  return [rows.filter((r) => r.available_at <= cutoffs.training),
    rows.filter((r) => r.available_at > cutoffs.training && r.decision_at > cutoffs.training && r.available_at <= cutoffs.calibration),
    rows.filter((r) => r.available_at > cutoffs.training && r.decision_at > cutoffs.calibration && r.available_at <= cutoffs.evaluation)];
}
function validateObservations(rows: Observation[], cutoffs: Cutoffs) {
  if (!(cutoffs.training < cutoffs.calibration && cutoffs.calibration < cutoffs.evaluation)) throw new Error("invalid cutoffs");
  const ids = new Set<string>(), lineages = new Set<string>();
  for (const r of rows) {
    if (ids.has(r.job_id) || lineages.has(r.project_lineage)) throw new Error("duplicate lineage");
    ids.add(r.job_id); lineages.add(r.project_lineage);
    if ((Date.parse(r.actual_complete) - Date.parse(r.actual_start)) / DAY !== r.duration_days) throw new Error("duration mismatch");
    if (!(r.features_available_at <= r.decision_at && r.decision_at <= `${r.actual_start}T00:00:00Z`)) throw new Error("feature leakage");
    if (!(`${r.actual_complete}T00:00:00Z` <= r.available_at && r.available_at <= cutoffs.evaluation)) throw new Error("outcome leakage");
    if ((r.planned_duration_days === null) !== (r.planned_available_at === null)
      || (r.planned_available_at !== null && r.planned_available_at > r.decision_at)) throw new Error("baseline leakage");
  }
}
export function evaluate(rows: Observation[], cutoffs: Cutoffs): Record<string, Evaluation> {
  validateObservations(rows, cutoffs);
  const [allTrain, allCal, allTest] = split(rows, cutoffs);
  const group = (items: Observation[], key: (row: Observation) => string) => {
    const groups = new Map<string, Observation[]>();
    for (const item of items) {
      const groupKey = key(item), values = groups.get(groupKey);
      if (values) values.push(item); else groups.set(groupKey, [item]);
    }
    return groups;
  };
  const [trainGroups, calGroups, testGroups] = [allTrain, allCal, allTest].map((items) => group(items, cohort));
  const baselines = group(allTrain, (row) => row.job_type);
  const result: Record<string, Evaluation> = {};
  for (const key of [...new Set(rows.map(cohort))].sort()) {
    const training = trainGroups.get(key) ?? [], calibration = calGroups.get(key) ?? [], holdout = testGroups.get(key) ?? [];
    const entry: Evaluation = { training: training.length, calibration: calibration.length, holdout: holdout.length,
      passed: false, reasons: [], interval: null, metrics: null, probability: null };
    result[key] = entry;
    if (training.length < 30 || calibration.length < 20 || holdout.length < 20) {
      entry.reasons.push("insufficient temporally separated cohort support"); continue;
    }
    const center = median(training.map((r) => r.duration_days));
    const residuals = calibration.map((r) => Math.abs(r.duration_days - center)).sort((a, b) => a - b);
    const radius = residuals[Math.min(residuals.length - 1, Math.ceil((residuals.length + 1) * 0.8) - 1)];
    const lower = Math.max(1, center - radius), upper = center + radius;
    const baselineRows = baselines.get(training[0].job_type)!;
    const baselineCenter = median(baselineRows.map((r) => r.duration_days));
    const mae = mean(holdout.map((r) => Math.abs(r.duration_days - center)));
    const baselineMae = mean(holdout.map((r) => Math.abs(r.duration_days - baselineCenter)));
    const coverage = mean(holdout.map((r) => Number(lower <= r.duration_days && r.duration_days <= upper)));
    entry.interval = { lower, median: center, upper };
    entry.metrics = { mae_days: mae, baseline_mae_days: baselineMae, interval_coverage: coverage };
    if (mae > baselineMae + 1e-9 || mae > 30 || mae > center * 0.35) entry.reasons.push("held-out duration error gate failed");
    if (coverage < 0.75 || upper - lower > 120 || upper - lower > 2 * center) entry.reasons.push("held-out interval coverage/width gate failed");
    entry.passed = !entry.reasons.length;
    const plans = training.flatMap((r) => r.planned_duration_days === null ? [] : [r.planned_duration_days]);
    if (plans.length < 30) continue;
    const domain = { lower: Math.min(...plans), upper: Math.max(...plans) };
    const supported = (r: Observation) => r.planned_duration_days !== null && domain.lower <= r.planned_duration_days && r.planned_duration_days <= domain.upper;
    const probCal = calibration.filter(supported), probTest = holdout.filter(supported);
    if (probCal.length < 20 || probTest.length < 20) continue;
    const brier = (sample: Observation[], distribution: Observation[]) => {
      const durations = distribution.map((r) => r.duration_days).sort((a, b) => a - b);
      return mean(sample.map((r) => {
        let low = 0, high = durations.length;
        while (low < high) {
          const mid = Math.floor((low + high) / 2);
          if (durations[mid] <= r.planned_duration_days!) low = mid + 1; else high = mid;
        }
        return ((durations.length - low) / durations.length - Number(r.duration_days > r.planned_duration_days!)) ** 2;
      }));
    };
    const calBrier = brier(probCal, training), testBrier = brier(probTest, training);
    const calBase = brier(probCal, baselineRows), testBase = brier(probTest, baselineRows);
    const covered = [probCal, probTest].every((sample) => Math.min(...sample.map((r) => r.planned_duration_days!)) <= domain.lower
      && Math.max(...sample.map((r) => r.planned_duration_days!)) >= domain.upper);
    entry.probability = { passed: covered && calBrier <= Math.min(0.2, calBase + 1e-9) && testBrier <= Math.min(0.2, testBase + 1e-9),
      domain, calibration: probCal.length, holdout: probTest.length, calibration_brier: calBrier, holdout_brier: testBrier,
      calibration_baseline_brier: calBase, holdout_baseline_brier: testBase };
  }
  return result;
}
function sameMetrics(actual: unknown, expected: unknown): boolean {
  if (typeof actual === "number" && typeof expected === "number") return Math.abs(actual - expected) <= 1e-9;
  if (actual === null || expected === null || typeof actual !== "object" || typeof expected !== "object") return actual === expected;
  const a = actual as Record<string, unknown>, b = expected as Record<string, unknown>;
  return canonical(Object.keys(a).sort()) === canonical(Object.keys(b).sort()) && Object.keys(a).every((k) => sameMetrics(a[k], b[k]));
}
export function validateArtifact(value: unknown, now: Date): Artifact {
  const artifact = ArtifactSchema.parse(value);
  const evaluated = Date.parse(artifact.cutoffs.evaluation);
  if (evaluated > now.getTime() || now.getTime() - evaluated > 180 * DAY) throw new Error("model future or expired");
  if (sha256(canonical(artifact.observations)) !== artifact.dataset_hash) throw new Error("dataset hash mismatch");
  if (sha256(canonical(artifact.provenance)) !== artifact.provenance_hash) throw new Error("provenance hash mismatch");
  const sources = artifact.provenance.sources;
  if (new Set(sources.map((s) => s.id)).size !== sources.length) throw new Error("duplicate audit source");
  const sourceHashes = new Set(sources.map((s) => s.sha256));
  const reviews = new Map(artifact.provenance.reviews.map((r) => [r.job_id, r]));
  if (reviews.size !== artifact.provenance.reviews.length || reviews.size !== artifact.observations.length) throw new Error("incomplete review audit");
  for (const source of sources) {
    if (!(source.published_at <= source.received_at && source.received_at <= source.reviewed_at && source.reviewed_at <= artifact.cutoffs.evaluation)) throw new Error("source audit times");
  }
  for (const row of artifact.observations) {
    const review = reviews.get(row.job_id);
    if (!row.evidence_hashes.every((h) => sourceHashes.has(h)) || review?.decision !== "accepted" || review.reviewed_at > row.available_at) throw new Error("unbound authorization/review");
  }
  const computed = evaluate(artifact.observations, artifact.cutoffs);
  if (!sameMetrics(artifact.evaluation, computed)) throw new Error("unsupported evaluation claims");
  return { ...artifact, evaluation: computed };
}

export type LoadedModel = { artifact: Artifact; version: string; approved_at: string } | null;
export type ModelEnvironment = { OUTCOMES_MODEL_PATH?: string; OUTCOMES_APPROVED_SHA256?: string; OUTCOMES_APPROVED_AT?: string };
export async function loadApprovedModel(env: ModelEnvironment, now = new Date()): Promise<LoadedModel> {
  const path = env.OUTCOMES_MODEL_PATH, approved = env.OUTCOMES_APPROVED_SHA256, approvedAt = env.OUTCOMES_APPROVED_AT;
  if (!path || !isAbsolute(path) || !approved || !hash.safeParse(approved).success || !approvedAt || !stamp.safeParse(approvedAt).success || Date.parse(approvedAt) > now.getTime()) return null;
  try {
    const resolved = await realpath(path);
    for (let directory = dirname(resolved);;) {
      const gitPresent = await access(join(directory, ".git")).then(() => true, () => false);
      if (gitPresent) return null;
      const parent = dirname(directory);
      if (parent === directory) break;
      directory = parent;
    }
    // Configuration is server-controlled; no request can supply a filename or hash.
    const file = await open(resolved, "r");
    let raw: Buffer;
    try {
      const stat = await file.stat();
      if (!stat.isFile() || stat.size > MAX_BYTES) return null;
      const buffer = Buffer.alloc(MAX_BYTES + 1);
      let offset = 0;
      while (offset < buffer.length) {
        const { bytesRead } = await file.read(buffer, offset, buffer.length - offset, offset);
        if (!bytesRead) break;
        offset += bytesRead;
      }
      if (offset > MAX_BYTES) return null;
      raw = buffer.subarray(0, offset);
    } finally { await file.close(); }
    if (sha256(raw) !== approved) return null;
    const artifact = validateArtifact(JSON.parse(raw.toString("utf8")), now);
    if (approvedAt < artifact.cutoffs.evaluation) return null;
    return { artifact, version: approved, approved_at: approvedAt };
  } catch { return null; } // Never expose source paths, private values or parser diagnostics.
}

export function createModelLoader() {
  let cached: { key: string; checked_at: number; pending: Promise<LoadedModel> } | null = null;
  return async (env: ModelEnvironment, now = new Date()): Promise<LoadedModel> => {
    if (!env.OUTCOMES_MODEL_PATH || !env.OUTCOMES_APPROVED_SHA256 || !env.OUTCOMES_APPROVED_AT) { cached = null; return null; }
    try {
      const path = await realpath(env.OUTCOMES_MODEL_PATH), info = await stat(path);
      const key = JSON.stringify([path, env.OUTCOMES_APPROVED_SHA256, env.OUTCOMES_APPROVED_AT, info.ino, info.size, info.mtimeMs, info.ctimeMs]);
      if (cached?.key !== key) cached = { key, checked_at: now.getTime(), pending: loadApprovedModel(env, now) };
      let loaded = await cached.pending;
      if (!loaded && now.getTime() - cached.checked_at >= 30_000) {
        cached = { key, checked_at: now.getTime(), pending: loadApprovedModel(env, now) };
        loaded = await cached.pending;
      }
      if (loaded && (now.getTime() - Date.parse(loaded.artifact.cutoffs.evaluation) > 180 * DAY || Date.parse(loaded.approved_at) > now.getTime())) return null;
      return loaded;
    } catch { cached = null; return null; }
  };
}

export type PredictionResponse = {
  status: "predicted" | "insufficient_evidence" | "unavailable" | "invalid";
  reason: string; request: PredictRequest | null;
  prediction: { duration_days: { lower: number; median: number; upper: number }; delay_probability: number | null } | null;
  support: { training: number; calibration: number; holdout: number } | null;
  evaluation: { passed: true; evaluated_at: string; mae_days: number; baseline_mae_days: number; interval_coverage: number } | null;
  model_version: string | null; limitations: string[];
  probability_evidence: { numerator: number; denominator: number; interval_95: { lower: number; upper: number }; interpretation: string } | null;
};
const LIMITATIONS = ["Physical construction start to physical construction complete, in calendar days; not an in-service milestone.",
  "Cohort associations do not establish company performance causes. Temporal holdout performance does not guarantee future accuracy.",
  "The duration interval targets 80% coverage and is evaluated empirically; changing conditions can reduce coverage."];
export function predict(loaded: LoadedModel, input: unknown, now = new Date()): PredictionResponse {
  const parsed = PredictRequestSchema.safeParse(input);
  const response: PredictionResponse = { status: "invalid", reason: "Invalid cohort, timestamp or baseline confirmation.", request: parsed.success ? parsed.data : null,
    prediction: null, support: null, evaluation: null, model_version: null, limitations: LIMITATIONS, probability_evidence: null };
  if (!parsed.success || Date.parse(parsed.data.as_of) > now.getTime()) return response;
  if (!loaded) return { ...response, status: "unavailable", reason: "No current, externally approved model from verified actual job histories is available." };
  const { artifact, version } = loaded, request = parsed.data;
  if (request.as_of < loaded.approved_at || request.as_of < artifact.cutoffs.evaluation || Date.parse(request.as_of) - Date.parse(artifact.cutoffs.evaluation) > 180 * DAY) {
    return { ...response, status: "insufficient_evidence", reason: "This model cannot support the requested decision time." };
  }
  const entry = artifact.evaluation[cohort(request)];
  if (!entry?.passed || !entry.interval) return { ...response, status: "insufficient_evidence", reason: "No cohort passes the required support and temporal evaluation gates." };
  let probability: number | null = null, probabilityEvidence: PredictionResponse["probability_evidence"] = null;
  const baseline = request.planned_duration_days, domain = entry.probability?.domain;
  if (baseline !== undefined && entry.probability?.passed && domain && domain.lower <= baseline && baseline <= domain.upper) {
    const training = split(artifact.observations, artifact.cutoffs)[0].filter((r) => cohort(r) === cohort(request));
    const successes = training.filter((r) => r.duration_days > baseline).length, n = training.length;
    probability = successes / n;
    const zScore = 1.959963984540054, den = 1 + zScore ** 2 / n;
    const center = (probability + zScore ** 2 / (2 * n)) / den;
    const radius = zScore * Math.sqrt(probability * (1 - probability) / n + zScore ** 2 / (4 * n ** 2)) / den;
    probabilityEvidence = { numerator: successes, denominator: n, interval_95: { lower: Math.max(0, center - radius), upper: Math.min(1, center + radius) },
      interpretation: "Empirical duration-overrun fraction against the user-provided planned duration; Wilson sampling interval, not a calibrated guarantee." };
  }
  return { ...response, status: "predicted", reason: "Cohort passed the declared temporal holdout gates.",
    prediction: { duration_days: entry.interval, delay_probability: probability },
    support: { training: entry.training, calibration: entry.calibration, holdout: entry.holdout },
    evaluation: { passed: true, evaluated_at: artifact.cutoffs.evaluation, mae_days: Math.round(entry.metrics!.mae_days),
      baseline_mae_days: Math.round(entry.metrics!.baseline_mae_days), interval_coverage: Math.round(entry.metrics!.interval_coverage * 20) / 20 },
    model_version: version, probability_evidence: probabilityEvidence,
    limitations: [...LIMITATIONS, ...(probability === null ? ["Duration-overrun probability withheld: a supported confirmed baseline and passing probability evaluation are required."] : ["Planned duration is user-provided, not independently verified."])] };
}
export function modelStatus(loaded: LoadedModel) {
  if (!loaded) return { status: "unavailable" as const, reason: "No current, externally approved model from verified actual job histories is available.",
    model_version: null, support: null, evaluation: null, limitations: LIMITATIONS };
  const count = Object.values(loaded.artifact.evaluation).filter((e) => e.passed).length;
  return { status: count ? "ready" as const : "insufficient_evidence" as const, reason: count ? "Evaluated cohorts are available; each request is checked separately." : "No cohort passes all evaluation gates.",
    model_version: loaded.version, support: { passing_cohorts: count }, evaluation: { cutoff: loaded.artifact.cutoffs.evaluation, policy: loaded.artifact.policy_version }, limitations: LIMITATIONS };
}
