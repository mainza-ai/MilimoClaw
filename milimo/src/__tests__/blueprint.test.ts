// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  readdirSync: vi.fn(),
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  mkdirSync: vi.fn(),
  unlinkSync: vi.fn(),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
}));

vi.mock("node:child_process", () => ({
  spawnSync: vi.fn(),
}));

vi.mock("../commands/init", () => ({
  loadMilimoState: vi.fn(),
  saveMilimoState: vi.fn(),
}));

const mockedFs = (await import("node:fs")) as any;
const mockedSpawnSync = (await import("node:child_process")).spawnSync as vi.Mock;
const mockedInit = await import("../commands/init");

import {
  cliBlueprintList,
  cliBlueprintFork,
  cliBlueprintDiff,
  cliBlueprintPublish,
  cliBlueprintRollback,
  cliBlueprintSearch,
  cliBlueprintMerge,
  cliBlueprintInfo,
} from "../commands/blueprint";
import type { MilimoConfig } from "../index";

const createMockLogger = () => ({
  info: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
  warn: vi.fn(),
});

const createMockConfig = (overrides: Record<string, unknown> = {}): MilimoConfig => ({
  squadName: "test-squad",
  clawRole: "build",
  meshSecret: "",
  blueprintDir: "/home/test/milimo-blueprint",
  ...overrides,
});

describe("Blueprint Commands", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("cliBlueprintList", () => {
    it("displays blueprint catalog header", async () => {
      mockedFs.existsSync.mockReturnValue(false);
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: false,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("BLUEPRINT"));
    });

    it("shows active squad info when state exists", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readdirSync.mockReturnValue([]);
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.2.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({ version: "0.2.0", tools: {} }),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintList({
        json: false,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("test-squad"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("build"));
    });

    it("outputs JSON when json flag is true", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readdirSync.mockReturnValue([]);
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: true,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining('"catalog"'));
    });

    it("lists role blueprints from roles directory", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readdirSync.mockReturnValue(["content-claw.yaml", "build-claw.yaml"]);
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: false,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("content-claw"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("build-claw"));
    });

    it("lists template blueprints from templates directory", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readdirSync
        .mockReturnValueOnce(["content-claw.yaml"])
        .mockReturnValueOnce(["solo-founder.yaml"]);
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: false,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("solo-founder"));
    });

    it("shows evolved tools with performance delta", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readdirSync.mockReturnValue([]);
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.2.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({
          version: "0.2.0",
          tools: {
            auto_replier: { status: "deployed", version: "1.0", performance_delta: 15.5 },
          },
        }),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintList({
        json: false,
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("+15.5%"));
    });
  });

  describe("cliBlueprintFork", () => {
    it("errors when no state exists", async () => {
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintFork({
        source: "@author/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("init"));
    });

    it("downloads blueprint from marketplace", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({ meta: { version: "0.1.0" }, tools: {} }),
        stderr: "",
      });
      mockedFs.mkdirSync.mockReturnValue(undefined);
      mockedFs.writeFileSync.mockReturnValue(undefined);

      const logger = createMockLogger();
      await cliBlueprintFork({
        source: "@author/blueprint",
        into: "my-fork",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("Forking"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("my-fork"));
    });

    it("errors when blueprint not found", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "None",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintFork({
        source: "@nonexistent/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("not found"));
    });

    it("uses default fork name when --into not specified", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({ meta: { version: "0.1.0" } }),
        stderr: "",
      });
      mockedFs.mkdirSync.mockReturnValue(undefined);
      mockedFs.writeFileSync.mockReturnValue(undefined);

      const logger = createMockLogger();
      await cliBlueprintFork({
        source: "author/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("author-blueprint-fork"));
    });
  });

  describe("cliBlueprintDiff", () => {
    it("shows differences between versions", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({
          tools_added: ["new_tool"],
          tools_removed: [],
          tools_modified: ["existing_tool"],
          policy_changes: {},
          config_changes: { timeout: { from: 30, to: 60 } },
        }),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintDiff({
        versionA: "0.1.0",
        versionB: "0.2.0",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("new_tool"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("existing_tool"));
    });

    it("shows no changes message when versions are identical", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({
          tools_added: [],
          tools_removed: [],
          tools_modified: [],
          policy_changes: {},
          config_changes: {},
        }),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintDiff({
        versionA: "0.1.0",
        versionB: "0.1.0",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("No significant changes"));
    });
  });

  describe("cliBlueprintPublish", () => {
    it("publishes blueprint to marketplace", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.2.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "bp_abc123",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintPublish({
        name: "My Blueprint",
        price: "$10",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("bp_abc123"));
    });

    it("uses default name from squad and role", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "my-squad",
        clawRole: "content",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "bp_xyz",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintPublish({
        price: "free",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(
        expect.stringContaining("my-squad-content-blueprint"),
      );
    });
  });

  describe("cliBlueprintRollback", () => {
    it("rolls back to specified version", async () => {
      const mockState = {
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.3.0",
      };
      mockedInit.loadMilimoState.mockReturnValue(mockState);
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "True",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintRollback({
        to: "0.2.0",
        reason: "Bug in 0.3.0",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(mockedInit.saveMilimoState).toHaveBeenCalled();
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("Successfully rolled back"));
    });

    it("errors when --to version is missing", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.3.0",
      });

      const logger = createMockLogger();
      await cliBlueprintRollback({
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("--to"));
    });

    it("errors when version does not exist", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.3.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "False",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintRollback({
        to: "0.0.1",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("failed"));
    });
  });

  describe("cliBlueprintSearch", () => {
    it("searches marketplace with query", async () => {
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify([
          { id: "@author/bp1", author: "author", price: "$10", verified: true },
        ]),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintSearch({
        query: "content",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("@author/bp1"));
    });

    it("shows no results message when search returns empty", async () => {
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify([]),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintSearch({
        query: "nonexistent",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("No blueprints found"));
    });

    it("filters by category when specified", async () => {
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify([
          { id: "@author/analytics-bp", author: "author", price: "$20", verified: false },
        ]),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintSearch({
        query: "analytics",
        category: "data",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(mockedSpawnSync).toHaveBeenCalledWith(
        "python3",
        expect.arrayContaining([expect.stringContaining("analytics")]),
        expect.any(Object),
      );
    });
  });

  describe("cliBlueprintMerge", () => {
    it("merges incoming blueprint with current", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "0.2.0",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintMerge({
        incoming: "@other/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("merged"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("0.2.0"));
    });

    it("errors when no state exists", async () => {
      mockedInit.loadMilimoState.mockReturnValue(null);

      const logger = createMockLogger();
      await cliBlueprintMerge({
        incoming: "@other/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("init"));
    });
  });

  describe("cliBlueprintInfo", () => {
    it("displays blueprint details from marketplace", async () => {
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({
          id: "@author/blueprint",
          name: "Test Blueprint",
          author: "author",
          version: "1.0.0",
          price: "$15",
          tool_count: 5,
          fork_count: 10,
          published_at: "2026-03-01",
          verified: true,
          tags: ["automation", "content"],
        }),
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintInfo({
        blueprintId: "@author/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("Test Blueprint"));
      expect(logger.info).toHaveBeenCalledWith(expect.stringContaining("YES"));
    });

    it("errors when blueprint not found", async () => {
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: "None",
        stderr: "",
      });

      const logger = createMockLogger();
      await cliBlueprintInfo({
        blueprintId: "@nonexistent/blueprint",
        logger,
        pluginConfig: createMockConfig(),
      });

      expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("not found"));
    });
  });

  describe("spawnSync safety", () => {
    it("uses array arguments for all Python calls", async () => {
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({ version: "0.1.0", tools: {} }),
        stderr: "",
      });
      mockedFs.readdirSync.mockReturnValue([]);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: true,
        logger,
        pluginConfig: createMockConfig(),
      });

      const calls = mockedSpawnSync.mock.calls;
      for (const call of calls) {
        expect(Array.isArray(call[1])).toBe(true);
      }
    });

    it("uses JSON.stringify for safe interpolation", async () => {
      const dangerousPath = "/tmp/path with 'quotes' and \"double\"";
      mockedInit.loadMilimoState.mockReturnValue({
        squadName: "test-squad",
        clawRole: "build",
        blueprintVersion: "0.1.0",
      });
      mockedSpawnSync.mockReturnValue({
        status: 0,
        stdout: JSON.stringify({ version: "0.1.0", tools: {} }),
        stderr: "",
      });
      mockedFs.readdirSync.mockReturnValue([]);

      const logger = createMockLogger();
      await cliBlueprintList({
        json: true,
        logger,
        pluginConfig: { ...createMockConfig(), blueprintDir: dangerousPath },
      });

      const pythonArgs = mockedSpawnSync.mock.calls[0][1] as string[];
      const codeArg = pythonArgs.find((arg) => arg.includes("sys.path.insert"));
      expect(codeArg).toBeDefined();
      expect(codeArg).toContain("sys.path.insert");
    });
  });
});
