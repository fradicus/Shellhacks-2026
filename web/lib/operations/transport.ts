import { createHash } from "node:crypto";

const HOSTS = new Set([
  "api.weather.gov",
  "sdmdataaccess.nrcs.usda.gov",
  "sdmdataaccess.sc.egov.usda.gov",
  "wzdx.wsdot.wa.gov",
  "routes.googleapis.com",
  "waterservices.usgs.gov",
  "api.tidesandcurrents.noaa.gov",
  "hazards.fema.gov",
  "fwspublicservices.wim.usgs.gov",
]);
export type Fetcher = typeof fetch;
export const digest = (value: unknown) => createHash("sha256").update(JSON.stringify(value)).digest("hex");
export type Transport = (url: string, init?: RequestInit, maxBytes?: number) => Promise<{ value: unknown; hash: string; retrieved: string }>;

export function transport(fetcher: Fetcher = fetch, timeoutMs = 7000): Transport {
  return async (url, init = {}, maxBytes = 2_000_000) => {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.port || !HOSTS.has(parsed.hostname)) throw new Error("Unapproved provider URL");
    const abort = new AbortController();
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = new Promise<never>((_, reject) => { timer = setTimeout(() => { abort.abort(); void reader?.cancel().catch(() => {}); reject(new Error("Provider deadline exceeded")); }, timeoutMs); });
    const work = async () => {
      const response = await fetcher(url, { ...init, redirect: "manual", cache: "no-store", signal: abort.signal });
      if (!response.ok || response.status >= 300 || !response.body) { void response.body?.cancel().catch(() => {}); throw new Error(`Provider HTTP ${response.status}`); }
      const length = Number(response.headers.get("content-length"));
      if (length > maxBytes) { void response.body.cancel().catch(() => {}); throw new Error("Provider response exceeds byte budget"); }
      reader = response.body.getReader();
      const chunks: Uint8Array[] = []; let size = 0;
      while (true) {
        const part = await reader.read();
        if (part.done) break;
        size += part.value.byteLength;
        if (size > maxBytes) throw new Error("Provider response exceeds byte budget");
        chunks.push(part.value);
      }
      const bytes = Buffer.concat(chunks);
      return { value: JSON.parse(bytes.toString("utf8")) as unknown, hash: createHash("sha256").update(bytes).digest("hex"), retrieved: new Date().toISOString() };
    };
    try { return await Promise.race([work(), deadline]); }
    finally { clearTimeout(timer); abort.abort(); void reader?.cancel().catch(() => {}); }
  };
}
