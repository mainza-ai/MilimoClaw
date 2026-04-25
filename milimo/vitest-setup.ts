import { vi } from "vitest";
import { createRequire } from "node:module";
import { resolve, dirname } from "node:path";
import { existsSync } from "node:fs";

const TS_EXTENSIONS = [".ts", ".tsx", ".js", ".mjs", ".cjs"];

function resolveModulePath(specifier: string, fromFile: string): string {
  if (specifier.startsWith("node:")) return specifier;

  const fromDir = dirname(fromFile);

  if (specifier.startsWith(".") || specifier.startsWith("/")) {
    for (const ext of TS_EXTENSIONS) {
      const candidate = resolve(fromDir, specifier + ext);
      if (existsSync(candidate)) return candidate;
      const indexCandidate = resolve(fromDir, specifier, "index" + ext);
      if (existsSync(indexCandidate)) return indexCandidate;
    }
    return resolve(fromDir, specifier);
  }

  return specifier;
}

function getCallerFile(): string | null {
  const stack = new Error().stack;
  if (!stack) return null;
  const lines = stack.split("\n");
  for (const line of lines) {
    if (line.includes("vitest-setup")) continue;
    const match =
      line.match(/\((.+):\d+:\d+\)/) ||
      line.match(/at\s+(.+):\d+:\d+/) ||
      line.match(/at\s+.+\s+\((.+):\d+:\d+\)/);
    if (match) {
      const filePath = match[1];
      if (filePath.endsWith(".ts") || filePath.endsWith(".tsx") || filePath.endsWith(".js")) {
        return filePath;
      }
    }
  }
  return null;
}

const mockCache = new Map<string, Record<string, unknown>>();

const originalMock = vi.mock.bind(vi) as typeof vi.mock;
const patchedMock = (path: string, factory?: Parameters<typeof vi.mock>[1]) => {
  if (factory && typeof factory === "function") {
    const callerFile = getCallerFile();
    const resolvedPath = callerFile ? resolveModulePath(path, callerFile) : path;
    const result = (factory as () => unknown)();
    if (result && typeof result === "object") {
      mockCache.set(resolvedPath, result as Record<string, unknown>);
      mockCache.set(path, result as Record<string, unknown>);
    }
  }
  return originalMock(path, factory);
};

Object.defineProperty(globalThis, "jest", {
  value: new Proxy(vi, {
    get(target, prop) {
      if (prop === "requireMock") {
        return (moduleName: string) => {
          if (mockCache.has(moduleName)) return mockCache.get(moduleName);

          const callerFile = getCallerFile();
          if (callerFile) {
            const resolvedPath = resolveModulePath(moduleName, callerFile);
            if (mockCache.has(resolvedPath)) return mockCache.get(resolvedPath);
          }

          try {
            if (callerFile) {
              const callerRequire = createRequire(callerFile);
              return callerRequire(moduleName);
            }
            return require(moduleName);
          } catch {
            return {};
          }
        };
      }
      if (prop === "createMockFromModule") {
        return (moduleName: string) => {
          if (mockCache.has(moduleName)) return mockCache.get(moduleName);

          const callerFile = getCallerFile();
          if (callerFile) {
            const resolvedPath = resolveModulePath(moduleName, callerFile);
            if (mockCache.has(resolvedPath)) return mockCache.get(resolvedPath);
          }

          try {
            if (callerFile) {
              const callerRequire = createRequire(callerFile);
              return callerRequire(moduleName);
            }
            return require(moduleName);
          } catch {
            return {};
          }
        };
      }
      if (prop === "mock") {
        return patchedMock;
      }
      return (target as any)[prop];
    },
  }),
  writable: false,
  configurable: true,
});
