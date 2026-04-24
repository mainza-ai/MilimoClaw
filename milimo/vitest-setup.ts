import { vi } from "vitest";

Object.defineProperty(globalThis, "jest", {
  value: new Proxy(vi, {
    get(target, prop) {
      if (prop === "requireMock") {
        return (moduleName: string) => require(moduleName);
      }
      if (prop === "createMockFromModule") {
        return (moduleName: string) => require(moduleName);
      }
      return (target as any)[prop];
    },
  }),
  writable: false,
  configurable: true,
});
