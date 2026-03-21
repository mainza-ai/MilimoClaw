// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for Action CLI commands
 */

import { join } from "node:path";
import {
  cliActionApprove,
  cliActionBlock,
  listPendingActions,
  type PendingAction,
  type Logger,
} from "../commands/action";

const mockLogger: Logger = {
  info: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
};

const mockExistsSync = jest.fn();
const mockReaddirSync = jest.fn();
const mockReadFileSync = jest.fn();
const mockRenameSync = jest.fn();
const mockWriteFileSync = jest.fn();
const mockUnlinkSync = jest.fn();
const mockMkdirSync = jest.fn();

jest.mock("node:fs", () => ({
  existsSync: (...args: unknown[]) => mockExistsSync(...args),
  readdirSync: (...args: unknown[]) => mockReaddirSync(...args),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
  renameSync: (...args: unknown[]) => mockRenameSync(...args),
  writeFileSync: (...args: unknown[]) => mockWriteFileSync(...args),
  unlinkSync: (...args: unknown[]) => mockUnlinkSync(...args),
  mkdirSync: (...args: unknown[]) => mockMkdirSync(...args),
}));

jest.mock("node:os", () => ({
  homedir: () => "/home/test",
}));

describe("Action CLI", () => {
  const pluginConfig = { blueprintDir: "/tmp/blueprint" };

  const mockAction: PendingAction = {
    message_id: "act_123",
    sender_role: "content",
    recipient_role: "war_room",
    message_type: "tool_proposal",
    payload: { tool_name: "test_tool" },
    squad_id: "test-squad",
    timestamp: "2026-03-20T10:00:00Z",
    needs_approval: true,
    file_path: "/home/test/.milimo/mesh/inbox/war_room/msg_001.json",
    priority: "REVIEW",
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockExistsSync.mockReset();
    mockReaddirSync.mockReset();
    mockReadFileSync.mockReset();
    mockRenameSync.mockReset();
    mockWriteFileSync.mockReset();
    mockUnlinkSync.mockReset();
    mockMkdirSync.mockReset();
  });

  describe("listPendingActions", () => {
    it("returns empty array when inbox does not exist", () => {
      mockExistsSync.mockReturnValue(false);

      const actions = listPendingActions();

      expect(actions).toEqual([]);
    });

    it("returns pending actions from inbox", () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json", "msg_002.json"]);
      mockReadFileSync
        .mockReturnValueOnce(JSON.stringify(mockAction))
        .mockReturnValueOnce(
          JSON.stringify({
            ...mockAction,
            message_id: "act_456",
          }),
        );

      const actions = listPendingActions();

      expect(actions).toHaveLength(2);
      expect(actions[0].message_id).toBe("act_123");
      expect(actions[1].message_id).toBe("act_456");
    });

    it("returns empty array on read error", () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockImplementation(() => {
        throw new Error("Read error");
      });

      const actions = listPendingActions();

      expect(actions).toEqual([]);
    });

    it("sorts actions by timestamp", () => {
      const action1 = { ...mockAction, message_id: "act_1", timestamp: "2026-03-20T12:00:00Z" };
      const action2 = { ...mockAction, message_id: "act_2", timestamp: "2026-03-20T10:00:00Z" };

      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json", "msg_002.json"]);
      mockReadFileSync
        .mockReturnValueOnce(JSON.stringify(action1))
        .mockReturnValueOnce(JSON.stringify(action2));

      const actions = listPendingActions();

      expect(actions[0].message_id).toBe("act_2");
      expect(actions[1].message_id).toBe("act_1");
    });
  });

  describe("cliActionApprove", () => {
    it("exits with error if inbox does not exist", async () => {
      mockExistsSync.mockReturnValue(false);

      const exitSpy = jest.spyOn(process, "exit").mockImplementation(() => {
        throw new Error("exit");
      });

      await expect(
        cliActionApprove({
          actionId: "act_123",
          logger: mockLogger,
          pluginConfig,
        }),
      ).rejects.toThrow("exit");

      expect(mockLogger.error).toHaveBeenCalledWith(expect.stringContaining("No pending actions"));

      exitSpy.mockRestore();
    });

    it("exits with error if action not found", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockReturnValue(JSON.stringify({ message_id: "act_other" }));

      const exitSpy = jest.spyOn(process, "exit").mockImplementation(() => {
        throw new Error("exit");
      });

      await expect(
        cliActionApprove({
          actionId: "act_123",
          logger: mockLogger,
          pluginConfig,
        }),
      ).rejects.toThrow("exit");

      expect(mockLogger.error).toHaveBeenCalledWith(expect.stringContaining("Action not found"));

      exitSpy.mockRestore();
    });

    it("approves action and moves file", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockReturnValue(JSON.stringify(mockAction));
      mockRenameSync.mockReturnValue(undefined);
      mockMkdirSync.mockReturnValue(undefined);
      mockWriteFileSync.mockReturnValue(undefined);

      await cliActionApprove({
        actionId: "act_123",
        logger: mockLogger,
        pluginConfig,
      });

      expect(mockRenameSync).toHaveBeenCalled();
      expect(mockLogger.info).toHaveBeenCalledWith(expect.stringContaining("Action approved"));
    });

    it("logs tool name for tool_proposal", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockReturnValue(JSON.stringify(mockAction));
      mockRenameSync.mockReturnValue(undefined);
      mockMkdirSync.mockReturnValue(undefined);
      mockWriteFileSync.mockReturnValue(undefined);

      await cliActionApprove({
        actionId: "act_123",
        logger: mockLogger,
        pluginConfig,
      });

      expect(mockLogger.info).toHaveBeenCalledWith(expect.stringContaining("test_tool"));
    });
  });

  describe("cliActionBlock", () => {
    it("exits with error if inbox does not exist", async () => {
      mockExistsSync.mockReturnValue(false);

      const exitSpy = jest.spyOn(process, "exit").mockImplementation(() => {
        throw new Error("exit");
      });

      await expect(
        cliActionBlock({
          actionId: "act_123",
          logger: mockLogger,
          pluginConfig,
        }),
      ).rejects.toThrow("exit");

      expect(mockLogger.error).toHaveBeenCalledWith(expect.stringContaining("No pending actions"));

      exitSpy.mockRestore();
    });

    it("blocks action with reason", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockReturnValue(JSON.stringify(mockAction));
      mockWriteFileSync.mockReturnValue(undefined);
      mockUnlinkSync.mockReturnValue(undefined);
      mockMkdirSync.mockReturnValue(undefined);

      await cliActionBlock({
        actionId: "act_123",
        reason: "Not approved",
        logger: mockLogger,
        pluginConfig,
      });

      expect(mockLogger.info).toHaveBeenCalledWith(expect.stringContaining("Action blocked"));
      expect(mockLogger.info).toHaveBeenCalledWith(expect.stringContaining("Not approved"));
    });

    it("blocks action without reason", async () => {
      mockExistsSync.mockReturnValue(true);
      mockReaddirSync.mockReturnValue(["msg_001.json"]);
      mockReadFileSync.mockReturnValue(JSON.stringify(mockAction));
      mockWriteFileSync.mockReturnValue(undefined);
      mockUnlinkSync.mockReturnValue(undefined);
      mockMkdirSync.mockReturnValue(undefined);

      await cliActionBlock({
        actionId: "act_123",
        logger: mockLogger,
        pluginConfig,
      });

      expect(mockLogger.info).toHaveBeenCalledWith(expect.stringContaining("Action blocked"));
    });
  });
});
