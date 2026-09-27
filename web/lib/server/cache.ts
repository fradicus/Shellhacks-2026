import "server-only";

import { stat } from "node:fs/promises";

/** Values keyed by an immutable identity: a release id, or a file's size and mtime. A new identity is a new entry, so
 * a re-published artifact or a flipped release pointer is never served stale; the oldest entries age out. A load that
 * fails is dropped at once, so a transient error is never cached. */
export class IdentityCache<V> {
  private readonly entries = new Map<string, Promise<V>>();
  private readonly max: number;
  constructor(max = 4) {
    this.max = max;
  }

  get(identity: string, load: () => Promise<V>): Promise<V> {
    const hit = this.entries.get(identity);
    if (hit) {
      this.entries.delete(identity);
      this.entries.set(identity, hit);
      return hit;
    }
    const pending = load();
    this.entries.set(identity, pending);
    pending.catch(() => {
      if (this.entries.get(identity) === pending) this.entries.delete(identity);
    });
    while (this.entries.size > this.max) this.entries.delete(this.entries.keys().next().value!);
    return pending;
  }

  /** Explicit invalidation, for a writer in this process that knows an identity is gone. */
  delete(identity: string): void {
    this.entries.delete(identity);
  }

  clear(): void {
    this.entries.clear();
  }

  get size(): number {
    return this.entries.size;
  }
}

/** A file's identity for caching: path, byte size and modification time. Any rewrite changes it. */
export async function fileIdentity(path: string): Promise<string> {
  const info = await stat(path);
  return `${path}:${info.size}:${info.mtimeMs}`;
}
