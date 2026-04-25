// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { OperatorNotifier, type NotificationPayload } from "../warroom/notifier";

const mockSpawnSync = vi.fn();
vi.mock("node:child_process", () => ({
  spawnSync: (...args: unknown[]) => mockSpawnSync(...args),
}));

const mockExistsSync = vi.fn();
const mockMkdirSync = vi.fn();
const mockReadFileSync = vi.fn();
const mockWriteFileSync = vi.fn();
const mockUnlinkSync = vi.fn();

vi.mock("node:fs", () => ({
  existsSync: (...args: unknown[]) => mockExistsSync(...args),
  mkdirSync: (...args: unknown[]) => mockMkdirSync(...args),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
  writeFileSync: (...args: unknown[]) => mockWriteFileSync(...args),
  unlinkSync: (...args: unknown[]) => mockUnlinkSync(...args),
}));

vi.mock("node:os", () => ({
  homedir: () => "/home/test",
}));

describe("OperatorNotifier", () => {
  const holdPayload: NotificationPayload = {
    action_id: "act_123",
    claw: "content",
    action_type: "tool_proposal",
    summary: "New tool deployment proposed",
    priority: "HOLD",
    timestamp: "2026-03-20T10:00:00Z",
  };

  const reviewPayload: NotificationPayload = {
    action_id: "act_456",
    claw: "finance",
    action_type: "invoice",
    summary: "Invoice needs review",
    priority: "REVIEW",
    timestamp: "2026-03-20T10:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSpawnSync.mockReset();
    mockExistsSync.mockReset();
    mockMkdirSync.mockReset();
    mockReadFileSync.mockReset();
    mockWriteFileSync.mockReset();
    mockUnlinkSync.mockReset();
  });

  describe("constructor", () => {
    it("creates notification directory if not exists", () => {
      mockExistsSync.mockReturnValue(false);

      new OperatorNotifier();

      expect(mockMkdirSync).toHaveBeenCalled();
    });

    it("skips directory creation if already exists", () => {
      mockExistsSync.mockReturnValue(true);

      new OperatorNotifier();

      expect(mockMkdirSync).not.toHaveBeenCalled();
    });
  });

  describe("notify", () => {
    it("returns disabled when notifier is disabled", () => {
      const notifier = new OperatorNotifier(false);

      const result = notifier.notify(holdPayload);

      expect(result).toEqual({ delivered: false, method: "disabled" });
    });

    it("returns disabled for non-HOLD priority", () => {
      const notifier = new OperatorNotifier(true);

      const result = notifier.notify(reviewPayload);

      expect(result).toEqual({ delivered: false, method: "disabled" });
    });

    it("uses osascript on macOS", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "darwin", configurable: true });

      mockSpawnSync.mockReturnValue({ status: 0 });

      const notifier = new OperatorNotifier(true);
      const result = notifier.notify(holdPayload);

      expect(mockSpawnSync).toHaveBeenCalledWith(
        "osascript",
        expect.arrayContaining(["-e"]),
        expect.any(Object),
      );
      expect(result).toEqual({ delivered: true, method: "osascript" });

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });

    it("uses notify-send on Linux", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "linux", configurable: true });

      mockSpawnSync.mockReturnValue({ status: 0 });

      const notifier = new OperatorNotifier(true);
      const result = notifier.notify(holdPayload);

      expect(mockSpawnSync).toHaveBeenCalledWith(
        "notify-send",
        expect.any(Array),
        expect.any(Object),
      );
      expect(result).toEqual({ delivered: true, method: "notify-send" });

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });

    it("falls back to pending file on macOS failure", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "darwin", configurable: true });

      mockSpawnSync.mockReturnValue({ status: 1 });
      mockExistsSync.mockReturnValue(false);

      const notifier = new OperatorNotifier(true);
      const result = notifier.notify(holdPayload);

      expect(result).toEqual({ delivered: true, method: "pending_file" });
      expect(mockWriteFileSync).toHaveBeenCalled();

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });

    it("falls back to pending file on Linux failure", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "linux", configurable: true });

      mockSpawnSync.mockReturnValue({ status: 1 });
      mockExistsSync.mockReturnValue(false);

      const notifier = new OperatorNotifier(true);
      const result = notifier.notify(holdPayload);

      expect(result).toEqual({ delivered: true, method: "pending_file" });

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });
  });

  describe("notifyHoldRelease", () => {
    it("returns disabled when notifier is disabled", () => {
      const notifier = new OperatorNotifier(false);

      const result = notifier.notifyHoldRelease("act_123");

      expect(result).toEqual({ delivered: false, method: "disabled" });
    });

    it("sends notification on macOS", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "darwin", configurable: true });

      mockSpawnSync.mockReturnValue({ status: 0 });

      const notifier = new OperatorNotifier(true);
      const result = notifier.notifyHoldRelease("act_123");

      expect(mockSpawnSync).toHaveBeenCalled();
      expect(result).toEqual({ delivered: true, method: "osascript" });

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });
  });

  describe("getPendingNotifications", () => {
    it("returns empty array when no pending file", () => {
      mockExistsSync.mockReturnValue(false);

      const notifier = new OperatorNotifier();
      const pending = notifier.getPendingNotifications();

      expect(pending).toEqual([]);
    });

    it("returns pending notifications from file", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify([holdPayload, reviewPayload]));

      const notifier = new OperatorNotifier();
      const pending = notifier.getPendingNotifications();

      expect(pending).toHaveLength(2);
      expect(pending[0].action_id).toBe("act_123");
    });

    it("returns empty array on parse error", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue("invalid json");

      const notifier = new OperatorNotifier();
      const pending = notifier.getPendingNotifications();

      expect(pending).toEqual([]);
    });
  });

  describe("clearPendingNotification", () => {
    it("removes specific notification from pending file", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify([holdPayload, reviewPayload]));

      const notifier = new OperatorNotifier();
      notifier.clearPendingNotification("act_123");

      expect(mockWriteFileSync).toHaveBeenCalled();
      const writtenData = mockWriteFileSync.mock.calls[0][1] as string;
      const remaining = JSON.parse(writtenData);
      expect(remaining).toHaveLength(1);
      expect(remaining[0].action_id).toBe("act_456");
    });

    it("deletes file when last notification cleared", () => {
      mockExistsSync.mockReturnValue(true);
      mockReadFileSync.mockReturnValue(JSON.stringify([holdPayload]));

      const notifier = new OperatorNotifier();
      notifier.clearPendingNotification("act_123");

      expect(mockUnlinkSync).toHaveBeenCalled();
    });
  });

  describe("clearAllPending", () => {
    it("deletes pending file", () => {
      mockExistsSync.mockReturnValue(true);

      const notifier = new OperatorNotifier();
      notifier.clearAllPending();

      expect(mockUnlinkSync).toHaveBeenCalled();
    });

    it("does nothing if file does not exist", () => {
      mockExistsSync.mockReturnValue(false);

      const notifier = new OperatorNotifier();
      notifier.clearAllPending();

      expect(mockUnlinkSync).not.toHaveBeenCalled();
    });
  });
});
