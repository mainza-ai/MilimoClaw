// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    projects: [
      {
      test: {
        name: "plugin",
        include: ["milimo/src/**/*.test.ts"],
        globals: true,
        setupFiles: ["milimo/vitest-setup.ts"],
        typecheck: {
          tsconfig: "milimo/tsconfig.test.json",
        },
      },
      },
    ],
    coverage: {
      provider: "v8",
      include: ["milimo/src/**/*.ts"],
      exclude: ["**/*.test.ts"],
      reporter: ["text", "json-summary"],
    },
  },
});
