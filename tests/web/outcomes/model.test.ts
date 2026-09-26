/** SYNTHETIC TEST ONLY: none of these histories or metrics are operational evidence. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, mkdtemp, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join, resolve, sep } from "node:path";
import test from "node:test";
import { canonical, evaluate, loadApprovedModel, modelStatus, predict, PredictRequestSchema, validateArtifact } from "../../../web/lib/outcomes/model.ts";

const fixture = JSON.parse(await readFile(new URL("./synthetic-model.testfixture.json", import.meta.url), "utf8"));
const NOW = new Date("2023-06-02T00:00:00Z");
const request = { job_type: "synthetic-type", company_id: "synthetic-company", region: "synthetic-region", as_of: "2023-06-02T00:00:00Z" };
const sha = (value: string) => createHash("sha256").update(value).digest("hex");
// Only this isolated test harness simulates the type of an externally approved real-history artifact.
const candidate = () => ({ ...structuredClone(fixture), purpose: "authorized_actual_history" });
const loaded = () => ({ artifact: validateArtifact(candidate(), NOW), version: "a".repeat(64) });

test("Python-built test fixture has exactly reproducible TypeScript hashes and held-out metrics", () => {
  const model = candidate();
  assert.equal(sha(canonical(model.observations)), model.dataset_hash);
  assert.deepEqual(evaluate(model.observations, model.cutoffs), model.evaluation);
  assert.equal(modelStatus(loaded()).status, "ready");
  assert.throws(() => validateArtifact(fixture, NOW), /authorized_actual_history/);
});

test("missing model never substitutes fixture; private paths and cohorts are absent from status", async () => {
  assert.equal(await loadApprovedModel({}, NOW), null);
  assert.equal(await loadApprovedModel({ OUTCOMES_MODEL_PATH: "https://attacker.test/model.json" }, NOW), null);
  const response = predict(null, request, NOW);
  assert.equal(response.status, "unavailable");
  assert.equal(response.prediction, null);
  assert.equal(response.support, null);
  const status = JSON.stringify(modelStatus(loaded()));
  assert.ok(!status.includes("synthetic-company") && !status.includes("synthetic-lineage") && !status.includes("synthetic-only"));
});

test("external deployment hash pin is required even for an internally consistent artifact", async () => {
  const directory = await mkdtemp(join(tmpdir(), "gridbridge-synthetic-f35-"));
  try {
    const path = join(directory, "synthetic-only.json"), raw = JSON.stringify(candidate());
    await writeFile(path, raw);
    assert.equal(await loadApprovedModel({ OUTCOMES_MODEL_PATH: path }, NOW), null);
    assert.equal(await loadApprovedModel({ OUTCOMES_MODEL_PATH: path, OUTCOMES_APPROVED_SHA256: "b".repeat(64) }, NOW), null);
    const approved = await loadApprovedModel({ OUTCOMES_MODEL_PATH: path, OUTCOMES_APPROVED_SHA256: sha(raw) }, NOW);
    assert.ok(approved);
    await writeFile(path, raw + " ");
    assert.equal(await loadApprovedModel({ OUTCOMES_MODEL_PATH: path, OUTCOMES_APPROVED_SHA256: sha(raw) }, NOW), null);
  } finally {
    const target = resolve(directory);
    if (!target.startsWith(resolve(tmpdir()) + sep) || !basename(target).startsWith("gridbridge-synthetic-f35-")) throw new Error("unsafe test cleanup path");
    await rm(target, { recursive: true });
  }
});

test("duration and overrun probability remain distinct and baseline confirmation is strict", () => {
  const duration = predict(loaded(), request, NOW);
  assert.equal(duration.status, "predicted");
  assert.deepEqual(duration.prediction?.duration_days, { lower: 28, median: 30, upper: 32 });
  assert.equal(duration.prediction?.delay_probability, null);
  assert.equal(predict(loaded(), { ...request, planned_duration_days: 40 }, NOW).status, "invalid");
  assert.equal(PredictRequestSchema.safeParse({ ...request, planned_duration_confirmed_at_as_of: true }).success, false);
  const supported = predict(loaded(), { ...request, planned_duration_days: 40, planned_duration_confirmed_at_as_of: true }, NOW);
  assert.equal(supported.prediction?.delay_probability, 0);
  assert.equal(supported.probability_evidence?.numerator, 0);
  assert.equal(supported.probability_evidence?.denominator, 30);
  assert.ok(supported.probability_evidence!.interval_95.upper > 0);
  for (const baseline of [1, 39, 41, 3650]) {
    assert.equal(predict(loaded(), { ...request, planned_duration_days: baseline, planned_duration_confirmed_at_as_of: true }, NOW).prediction?.delay_probability, null);
  }
});

test("forged counts, forged metrics, repeated projects and impossible dates fail validation", () => {
  for (const alter of [
    (model: ReturnType<typeof candidate>) => { model.evaluation[Object.keys(model.evaluation)[0]].training = 9999; },
    (model: ReturnType<typeof candidate>) => { model.observations[0].duration_days = 100; model.dataset_hash = sha(canonical(model.observations)); },
    (model: ReturnType<typeof candidate>) => { model.observations[1].project_lineage = model.observations[0].project_lineage; model.dataset_hash = sha(canonical(model.observations)); },
    (model: ReturnType<typeof candidate>) => { model.observations[0].actual_start = "2021-02-30"; model.dataset_hash = sha(canonical(model.observations)); },
    (model: ReturnType<typeof candidate>) => { model.observations[0].features_available_at = "2025-01-01T00:00:00Z"; model.dataset_hash = sha(canonical(model.observations)); },
  ]) {
    const model = candidate(); alter(model);
    assert.throws(() => validateArtifact(model, NOW));
  }
});

test("future, expired, hindsight and unknown-cohort predictions abstain without small-cell disclosures", () => {
  assert.throws(() => validateArtifact(candidate(), new Date("2022-01-01T00:00:00Z")));
  assert.throws(() => validateArtifact(candidate(), new Date("2024-01-01T00:00:00Z")));
  assert.equal(predict(loaded(), { ...request, as_of: "2024-01-01T00:00:00Z" }, NOW).status, "invalid");
  assert.equal(predict(loaded(), { ...request, as_of: "2022-01-01T00:00:00Z" }, NOW).status, "insufficient_evidence");
  const unknown = predict(loaded(), { ...request, company_id: "unknown" }, NOW);
  assert.equal(unknown.status, "insufficient_evidence");
  assert.equal(unknown.support, null);
  assert.equal(unknown.evaluation, null);
  for (const bad of [NaN, Infinity, -1, 0, 1.5, "40"]) {
    assert.equal(predict(loaded(), { ...request, planned_duration_days: bad, planned_duration_confirmed_at_as_of: true }, NOW).status, "invalid");
  }
  assert.equal(predict(loaded(), { ...request, model_path: "/private/model.json" }, NOW).status, "invalid");
});
