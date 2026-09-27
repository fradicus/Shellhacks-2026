// One cached MongoClient per server instance (read-only user). Never logs the connection string.
import { MongoClient, type Db } from "mongodb";

export class DbUnavailable extends Error {}

const cache = globalThis as unknown as { __gridbridgeMongo?: Promise<MongoClient> };

export async function getDb(): Promise<Db> {
  const uri = process.env.MONGODB_URI_RO;
  if (!uri) throw new DbUnavailable("database not configured");
  cache.__gridbridgeMongo ??= new MongoClient(uri, {
    appName: "gridbridge-web",
    serverSelectionTimeoutMS: 5000,
    maxPoolSize: 5,
    readPreference: "primaryPreferred",
  })
    .connect()
    .catch((err: unknown) => {
      cache.__gridbridgeMongo = undefined; // retry on the next request instead of caching the failure
      throw new DbUnavailable(`database unreachable (${err instanceof Error ? err.name : "error"})`);
    });
  return (await cache.__gridbridgeMongo).db(process.env.MONGODB_DB ?? "gridbridge");
}

/** The dataset (git sha) the loader last activated. The API only ever reads this dataset. */
export async function activeDataset(db: Db, signal?: AbortSignal): Promise<string> {
  const meta = await db.collection<{ _id: string; dataset?: string }>("meta").findOne({ _id: "active" }, { maxTimeMS: 5_000, signal });
  if (!meta?.dataset) throw new DbUnavailable("no active dataset loaded");
  return meta.dataset;
}
