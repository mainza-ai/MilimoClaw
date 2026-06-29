// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { vi } from "vitest";

const mockReadFileSync = vi.fn();
const mockExistsSync = vi.fn();
const mockConsoleLog = vi.spyOn(console, "log").mockImplementation(() => {});
vi.spyOn(console, "error").mockImplementation(() => {});

// Mock the RPC bridge
const mockRpcCall = vi.fn();
vi.mock("../lib/rpc-bridge", () => ({
  getRpcClient: vi.fn(() => ({
    call: mockRpcCall,
  })),
}));

vi.mock("node:fs", () => ({
  existsSync: (...args: unknown[]) => mockExistsSync(...args),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
  dirname: vi.fn((p: string) => p.split("/").slice(0, -1).join("/")),
}));

vi.mock("node:os", () => ({
  homedir: vi.fn(() => "/home/test"),
}));

import {
  getAssistantConfig,
  assistantSetup,
  assistantVerify,
  assistantStart,
} from "../commands/assistant";

describe("assistant commands", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReadFileSync.mockReset();
    mockExistsSync.mockReset();
  });

  describe("getAssistantConfig", () => {
    it("returns null when config file does not exist", () => {
      mockExistsSync.mockReturnValue(false);
      const result = getAssistantConfig();
      expect(result).toBeNull();
    });

    it("returns config when assistant name is set", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        }),
      );
      const result = getAssistantConfig();
      expect(result).toEqual({ name: "Nova", emoji: "🦅" });
    });

    it("returns null when assistant name is missing", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({ assistant: {} }));
      const result = getAssistantConfig();
      expect(result).toBeNull();
    });

    it("uses default emoji when not set", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify({ assistant: { name: "Rex" } }));
      const result = getAssistantConfig();
      expect(result?.emoji).toBe("🦀");
    });
  });

  describe("assistantSetup", () => {
    it("calls rpc assistant_setup with blueprintDir", async () => {
      mockExistsSync.mockReturnValue(false);
      mockRpcCall.mockResolvedValue({});

      await assistantSetup();

      expect(mockRpcCall).toHaveBeenCalledWith("assistant_setup", {
        blueprintDir: "/home/test/.openclaw/milimo/blueprints/0.1.0",
      });
    });

    it("rejects on rpc failure", async () => {
      mockExistsSync.mockReturnValue(false);
      mockRpcCall.mockRejectedValue(new Error("RPC failed"));

      await expect(assistantSetup()).rejects.toThrow("RPC failed");
    });
  });

  describe("assistantVerify", () => {
    it("calls rpc assistant_verify and prints completion message", async () => {
      mockExistsSync.mockReturnValue(false);
      mockRpcCall.mockResolvedValue({});

      await assistantVerify();

      expect(mockRpcCall).toHaveBeenCalledWith("assistant_verify", {
        scriptPath: "/home/test/.openclaw/milimo/blueprints/0.1.0/orchestrator/assistant_setup.py",
        blueprintDir: "/home/test/.openclaw/milimo/blueprints/0.1.0",
      });
    });

    it("rejects when verification fails", async () => {
      mockExistsSync.mockReturnValue(false);
      mockRpcCall.mockRejectedValue(new Error("Verification failed"));

      await expect(assistantVerify()).rejects.toThrow("Assistant setup verification failed");
    });
  });

  describe("assistantStart", () => {
    it("exits when agent config does not exist", async () => {
      mockExistsSync.mockReturnValue(false);

      const mockExit = vi.spyOn(process, "exit").mockImplementation((() => {
        throw new Error("process.exit");
      }) as never);

      await expect(assistantStart()).rejects.toThrow("process.exit");

      expect(mockExit).toHaveBeenCalledWith(1);
      mockExit.mockRestore();
    });

    it("prints instruction message when config exists", async () => {
      mockExistsSync.mockImplementation((p: string) => {
        if (p.includes("config.yaml") || p.includes("config.json")) return true;
        return false;
      });
      mockReadFileSync.mockReturnValue(
        JSON.stringify({
          assistant: { name: "Nova", emoji: "🦅" },
        }),
      );

      await assistantStart();

      expect(mockConsoleLog).toHaveBeenCalledWith(expect.stringContaining("Starting Nova"));
      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining("openclaw tui --session main"),
      );
    });

    it("uses default name when assistant config missing", async () => {
      mockExistsSync.mockImplementation((p: string) => {
        if (p.includes("config.yaml") || p.includes("config.json")) return true;
        return false;
      });
      mockReadFileSync.mockReturnValue(JSON.stringify({}));

      await assistantStart();

      expect(mockConsoleLog).toHaveBeenCalledWith(
        expect.stringContaining("Starting your assistant"),
      );
    });
  });
});
