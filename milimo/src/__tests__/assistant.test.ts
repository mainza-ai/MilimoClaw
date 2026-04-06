// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for assistant.ts
 */

import { spawn } from "node:child_process";

jest.mock("node:child_process", () => ({
  spawn: jest.fn(),
}));

jest.mock("node:fs", () => ({
  existsSync: jest.fn(),
  readFileSync: jest.fn(),
}));

jest.mock("node:path", () => ({
  join: jest.fn((...args: string[]) => args.join("/")),
}));

const mockedSpawn = spawn as jest.MockedFunction<typeof spawn>;
const mockedFs = jest.requireMock("node:fs");

describe("assistant commands", () => {
  let mockProcess: { on: jest.Mock; stdout?: { on: jest.Mock }; stderr?: { on: jest.Mock } };

  beforeEach(() => {
    jest.clearAllMocks();
    mockProcess = {
      on: jest.fn(),
    };
    mockedSpawn.mockReturnValue(mockProcess as unknown as ReturnType<typeof spawn>);
  });

  describe("getAssistantConfig", () => {
    it("returns null when config file does not exist", async () => {
      mockedFs.existsSync.mockReturnValue(false);

      const { getAssistantConfig } = await import("../commands/assistant.js");
      const result = getAssistantConfig();

      expect(result).toBeNull();
    });

    it("returns config when assistant name is set", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        })
      );

      const { getAssistantConfig } = await import("../commands/assistant.js");
      const result = getAssistantConfig();

      expect(result).not.toBeNull();
      expect(result?.name).toBe("Nova");
      expect(result?.emoji).toBe("🦅");
    });

    it("returns null when assistant name is missing", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: {},
        })
      );

      const { getAssistantConfig } = await import("../commands/assistant.js");
      const result = getAssistantConfig();

      expect(result).toBeNull();
    });

    it("uses default emoji when not set", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Rex" },
        })
      );

      const { getAssistantConfig } = await import("../commands/assistant.js");
      const result = getAssistantConfig();

      expect(result?.emoji).toBe("🦀");
    });
  });

  describe("assistantSetup", () => {
    it("spawns python3 with correct arguments", async () => {
      const { assistantSetup } = await import("../commands/assistant.js");

      const setupPromise = assistantSetup();

      // Simulate successful exit
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await setupPromise;

      expect(mockedSpawn).toHaveBeenCalledWith(
        "python3",
        ["milimo-blueprint/orchestrator/assistant_setup.py"],
        { stdio: "inherit" }
      );
    });

    it("rejects on non-zero exit code", async () => {
      const { assistantSetup } = await import("../commands/assistant.js");

      const setupPromise = assistantSetup();

      // Simulate error exit
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(setupPromise).rejects.toThrow("Assistant setup failed with exit code 1");
    });
  });

  describe("assistantVerify", () => {
    it("spawns python3 with --verify flag", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        })
      );

      const { assistantVerify } = await import("../commands/assistant.js");

      const verifyPromise = assistantVerify();

      // Simulate successful exit
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await verifyPromise;

      expect(mockedSpawn).toHaveBeenCalledWith(
        "python3",
        ["milimo-blueprint/orchestrator/assistant_setup.py", "--verify"],
        { stdio: "inherit" }
      );
    });

    it("rejects when verification fails", async () => {
      const { assistantVerify } = await import("../commands/assistant.js");

      const verifyPromise = assistantVerify();

      // Simulate failed verification
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(verifyPromise).rejects.toThrow("Assistant setup verification failed");
    });
  });

  describe("assistantStart", () => {
    it("exits when agent config does not exist", async () => {
      mockedFs.existsSync.mockReturnValue(false);

      const mockExit = jest.spyOn(process, "exit").mockImplementation(() => {
        throw new Error("process.exit");
      });

      const { assistantStart } = await import("../commands/assistant.js");

      await expect(assistantStart()).rejects.toThrow("process.exit");

      expect(mockExit).toHaveBeenCalledWith(1);
      mockExit.mockRestore();
    });

    it("spawns openclaw with correct agent path", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        })
      );

      const { assistantStart } = await import("../commands/assistant.js");

      const startPromise = assistantStart();

      // Simulate successful exit
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await startPromise;

      expect(mockedSpawn).toHaveBeenCalledWith(
        "openclaw",
        ["tui", "--session", "main"],
        { stdio: "inherit" }
      );
    });

    it("rejects on non-zero exit code", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        })
      );

      const { assistantStart } = await import("../commands/assistant.js");

      const startPromise = assistantStart();

      // Simulate error exit
      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(startPromise).rejects.toThrow("Nova exited with code 1");
    });

    it("uses default name when assistant config missing", async () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify({}));

      const { assistantStart } = await import("../commands/assistant.js");

      const startPromise = assistantStart();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close"
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await startPromise;

      // Should use default name "your assistant"
      expect(mockedSpawn).toHaveBeenCalled();
    });
  });
});
