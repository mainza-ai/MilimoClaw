// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const mockReadFileSync = vi.fn();

vi.mock("node:child_process", () => ({
  spawn: vi.fn(),
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
}));

vi.mock("node:os", () => ({
  homedir: vi.fn(() => "/home/test"),
}));

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import {
  getAssistantConfig,
  assistantSetup,
  assistantVerify,
  assistantStart,
} from "../commands/assistant";

const mockedSpawn = spawn as vi.MockedFunction<typeof spawn>;
const mockedExistsSync = existsSync as vi.MockedFunction<typeof existsSync>;

describe("assistant commands", () => {
  let mockProcess: { on: vi.Mock; stdout?: { on: vi.Mock }; stderr?: { on: vi.Mock } };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockProcess = {
      on: vi.fn(),
    };
    mockedSpawn.mockReturnValue(mockProcess as unknown as ReturnType<typeof spawn>);
    mockReadFileSync.mockReset();
    mockedExistsSync.mockReset();
  });

  describe("getAssistantConfig", () => {
    it("returns null when config file does not exist", () => {
      mockedExistsSync.mockReturnValue(false);

      const result = getAssistantConfig();

      expect(result).toBeNull();
    });

    it("returns config when assistant name is set", () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        }),
      );

      const result = getAssistantConfig();

      expect(result).not.toBeNull();
      expect(result?.name).toBe("Nova");
      expect(result?.emoji).toBe("🦅");
    });

    it("returns null when assistant name is missing", () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: {},
        }),
      );

      const result = getAssistantConfig();

      expect(result).toBeNull();
    });

    it("uses default emoji when not set", () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({ assistant: { name: "Rex" } }));

      const result = getAssistantConfig();

      expect(result?.emoji).toBe("🦀");
    });
  });

  describe("assistantSetup", () => {
    it("spawns python3 with resolved script path", async () => {
      mockedExistsSync.mockReturnValue(false);

      const setupPromise = assistantSetup();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await setupPromise;

      expect(mockedSpawn).toHaveBeenCalledWith(
        "python3",
        ["/home/test/.milimo/blueprints/0.1.0/orchestrator/assistant_setup.py"],
        { stdio: "inherit" },
      );
    });

    it("rejects on non-zero exit code", async () => {
      mockedExistsSync.mockReturnValue(false);

      const setupPromise = assistantSetup();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(setupPromise).rejects.toThrow("Assistant setup failed with exit code 1");
    });
  });

  describe("assistantVerify", () => {
    it("spawns python3 with resolved script path and --verify flag", async () => {
      mockedExistsSync.mockReturnValue(false);

      const verifyPromise = assistantVerify();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await verifyPromise;

      expect(mockedSpawn).toHaveBeenCalledWith(
        "python3",
        ["/home/test/.milimo/blueprints/0.1.0/orchestrator/assistant_setup.py", "--verify"],
        { stdio: "inherit" },
      );
    });

    it("rejects when verification fails", async () => {
      mockedExistsSync.mockReturnValue(false);

      const verifyPromise = assistantVerify();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(verifyPromise).rejects.toThrow("Assistant setup verification failed");
    });
  });

  describe("assistantStart", () => {
    it("exits when agent config does not exist", async () => {
      mockedExistsSync.mockReturnValue(false);

      const mockExit = vi.spyOn(process, "exit").mockImplementation((() => {
        throw new Error("process.exit");
      }) as never);

      await expect(assistantStart()).rejects.toThrow("process.exit");

      expect(mockExit).toHaveBeenCalledWith(1);
      mockExit.mockRestore();
    });

    it("spawns openclaw with correct agent path", async () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        }),
      );

      const startPromise = assistantStart();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await startPromise;

      expect(mockedSpawn).toHaveBeenCalledWith("openclaw", ["tui", "--session", "main"], {
        stdio: "inherit",
      });
    });

    it("rejects on non-zero exit code", async () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        }),
      );

      const startPromise = assistantStart();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(1);

      await expect(startPromise).rejects.toThrow("Nova exited with code 1");
    });

    it("uses default name when assistant config missing", async () => {
      mockedExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({}));

      const startPromise = assistantStart();

      const closeCallback = mockProcess.on.mock.calls.find(
        (call: unknown[]) => call[0] === "close",
      )?.[1] as (code: number) => void;
      closeCallback?.(0);

      await startPromise;

      expect(mockedSpawn).toHaveBeenCalled();
    });
  });
});
