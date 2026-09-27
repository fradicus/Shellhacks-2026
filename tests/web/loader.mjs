// Resolve hook for every Node unit suite (scripts/run_node_tests.mjs). Node's type stripping runs the web sources as
// they are, but those sources follow the bundler convention: `@/` means web/, and relative value imports omit `.ts`.
// Test files themselves import with explicit extensions; this hook only bridges what the app code does.
import { registerHooks } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../web");
const EXTENSIONS = [".ts", ".mts", "/index.ts"];
const hasExtension = (specifier) => /\.[cm]?[jt]sx?$|\.json$/i.test(specifier);

registerHooks({
  resolve(specifier, context, next) {
    // Next's server-only guard throws outside the React server condition; unit tests are server-side by definition.
    if (specifier === "server-only") return { url: "data:text/javascript,export {}", shortCircuit: true };
    const target = specifier.startsWith("@/") ? pathToFileURL(path.join(WEB, specifier.slice(2))).href : specifier;
    try {
      return next(target, context);
    } catch (error) {
      const local = target.startsWith(".") || target.startsWith("file:");
      if (hasExtension(target)) throw error;
      // CommonJS packages without an exports map (next/navigation, next/server) resolve by file name under ESM.
      if (!local) {
        if (!/^(@[^/]+\/)?[^/]+\/.+/.test(target)) throw error;
        try {
          return next(`${target}.js`, context);
        } catch {
          throw error;
        }
      }
      for (const extension of EXTENSIONS) {
        try {
          return next(`${target}${extension}`, context);
        } catch {
          // try the next convention
        }
      }
      throw error;
    }
  },
});
