// Explicit public-only verification, never a normal test or paid/API-key call.
import { writeFile } from "node:fs/promises";
import { weather, soil, roadwork } from "../../../web/lib/operations/providers.ts";
import { water } from "../../../web/lib/operations/water.ts";
import { transport } from "../../../web/lib/operations/transport.ts";
if (!process.argv.includes("--allow-public-network")) throw new Error("Public network opt-in required");
const point = { lat: 47.6062, lon: -122.3321 };
const ctx = { now: new Date(), io: transport(), userAgent: "GridBridge/1.0 (https://github.com/fradicus/Shellhacks-2026)" };
const values = await Promise.all([weather(point, ctx), soil(point, ctx), roadwork(point, ctx), water(point, ctx)]);
const evidence = { schema_version: "operations-public-probe-v1", retrieved_at: new Date().toISOString(), point, paid_calls: 0, providers: values.map((v) => ({ provider: v.provider, status: v.status, source_url: v.source_url, source_updated_at: v.source_updated_at, evidence_hash: v.evidence_hash, coverage: v.coverage, limitations: v.limitations })) };
await writeFile(new URL("../../../data/environment/public-probe.json", import.meta.url), JSON.stringify(evidence, null, 2) + "\n");
console.log(JSON.stringify(evidence, null, 2));
