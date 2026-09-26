import { MongoClient } from "mongodb";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROBE_TIMEOUT_MS = 2_000;
const DRIVER_TIMEOUT_MS = 1_900;

type DbState = "up" | "down" | "not_configured";

type Health = {
  ok: boolean;
  commit: string | null;
  db: DbState;
  active_dataset: string | null;
};

class ProbeTimeout extends Error {}

async function probe(uri: string, signal: AbortSignal): Promise<string | null> {
  const client = new MongoClient(uri, {
    appName: "gridbridge-health",
    connectTimeoutMS: DRIVER_TIMEOUT_MS,
    serverSelectionTimeoutMS: DRIVER_TIMEOUT_MS,
    socketTimeoutMS: DRIVER_TIMEOUT_MS,
    timeoutMS: DRIVER_TIMEOUT_MS,
    maxPoolSize: 1,
    readPreference: "primaryPreferred",
  });

  try {
    const db = client.db(process.env.MONGODB_DB ?? "gridbridge");
    const [ping, meta] = await Promise.all([
      db.command({ ping: 1 }, { signal }),
      db
        .collection<{ _id: string; dataset?: unknown }>("meta")
        .findOne({ _id: "active" }, { projection: { dataset: 1 }, signal }),
    ]);
    if (ping.ok !== 1) throw new Error("database ping failed");
    const dataset = meta?.dataset;
    return typeof dataset === "string" && dataset.trim().length > 0 ? dataset : null;
  } finally {
    await client.close().catch(() => undefined);
  }
}

async function boundedProbe(uri: string): Promise<string | null> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new ProbeTimeout("database probe timed out"));
    }, PROBE_TIMEOUT_MS);
  });

  try {
    return await Promise.race([probe(uri, controller.signal), deadline]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function response(body: Health, status: number): Response {
  return Response.json(body, {
    status,
    headers: { "Cache-Control": "no-store" },
  });
}

export async function GET(): Promise<Response> {
  const commit = process.env.VERCEL_GIT_COMMIT_SHA ?? null;
  const uri = process.env.MONGODB_URI_RO;

  if (!uri) {
    return response({ ok: false, commit, db: "not_configured", active_dataset: null }, 503);
  }

  try {
    const activeDataset = await boundedProbe(uri);
    if (!activeDataset) {
      return response({ ok: false, commit, db: "up", active_dataset: null }, 503);
    }
    return response({ ok: true, commit, db: "up", active_dataset: activeDataset }, 200);
  } catch {
    return response({ ok: false, commit, db: "down", active_dataset: null }, 503);
  }
}
