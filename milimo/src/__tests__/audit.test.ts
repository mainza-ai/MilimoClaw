// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for Audit Logger with rotation
 */

import { AuditLogger, type AuditEntry } from "../warroom/audit";

const mockExistsSync = jest.fn();
const mockMkdirSync = jest.fn();
const mockWriteFileSync = jest.fn();
const mockAppendFileSync = jest.fn();
const mockReadFileSync = jest.fn();
const mockReaddirSync = jest.fn();
const mockStatSync = jest.fn();
const mockRenameSync = jest.fn();
const mockUnlinkSync = jest.fn();
const mockGzipSync = jest.fn();
const mockGunzipSync = jest.fn();

jest.mock("node:fs", () => ({
  existsSync: (...args: unknown[]) => mockExistsSync(...args),
  mkdirSync: (...args: unknown[]) => mockMkdirSync(...args),
  writeFileSync: (...args: unknown[]) => mockWriteFileSync(...args),
  appendFileSync: (...args: unknown[]) => mockAppendFileSync(...args),
  readFileSync: (...args: unknown[]) => mockReadFileSync(...args),
  readdirSync: (...args: unknown[]) => mockReaddirSync(...args),
  statSync: (...args: unknown[]) => mockStatSync(...args),
  renameSync: (...args: unknown[]) => mockRenameSync(...args),
  unlinkSync: (...args: unknown[]) => mockUnlinkSync(...args),
}));

jest.mock("node:zlib", () => ({
  gzipSync: (...args: unknown[]) => mockGzipSync(...args),
  gunzipSync: (...args: unknown[]) => mockGunzipSync(...args),
}));

jest.mock("node:os", () => ({
  homedir: () => "/home/test",
}));

describe("AuditLogger", () => {
  const squadId = "test-squad";

  beforeEach(() => {
    jest.clearAllMocks();
    mockExistsSync.mockReturnValue(true);
    mockMkdirSync.mockReturnValue(undefined);
    mockAppendFileSync.mockReturnValue(undefined);
    mockStatSync.mockReturnValue({
      mtime: new Date(),
      size: 1024,
    });
  });

  describe("constructor", () => {
    it("creates audit directory if not exists", () => {
      mockExistsSync.mockReturnValue(false);

      new AuditLogger(squadId);

      expect(mockMkdirSync).toHaveBeenCalledWith(
        expect.stringContaining(".milimo/audit"),
        { recursive: true }
      );
    });

    it("skips directory creation if exists", () => {
      mockExistsSync.mockReturnValue(true);

      new AuditLogger(squadId);

      expect(mockMkdirSync).not.toHaveBeenCalled();
    });
  });

  describe("logAction", () => {
    it("appends entry to log file", () => {
      const logger = new AuditLogger(squadId);

      logger.logAction({
        actionType: "test_action",
        clawRole: "content",
        decision: "APPROVED",
      });

      expect(mockAppendFileSync).toHaveBeenCalledWith(
        expect.stringContaining("warroom.log"),
        expect.stringContaining("test_action"),
        "utf8"
      );
    });

    it("includes timestamp in entry", () => {
      const logger = new AuditLogger(squadId);

      logger.logAction({
        actionType: "test_action",
      });

      const written = mockAppendFileSync.mock.calls[0][1] as string;
      const entry = JSON.parse(written) as AuditEntry;
      expect(entry.timestamp).toBeDefined();
    });
  });

  describe("getRecentLogs", () => {
    it("returns empty array if file does not exist", () => {
      mockExistsSync.mockReturnValue(false);
      const logger = new AuditLogger(squadId);

      const logs = logger.getRecentLogs();

      expect(logs).toEqual([]);
    });

    it("returns parsed log entries", () => {
      mockReadFileSync.mockReturnValue(
        JSON.stringify({ actionType: "action1", timestamp: "2026-01-01T00:00:00Z" }) + "\n" +
        JSON.stringify({ actionType: "action2", timestamp: "2026-01-01T00:01:00Z" }) + "\n"
      );

      const logger = new AuditLogger(squadId);
      const logs = logger.getRecentLogs();

      expect(logs).toHaveLength(2);
      expect(logs[0].actionType).toBe("action1");
    });

    it("limits returned entries", () => {
      const entries = Array(100)
        .fill(null)
        .map((_, i) => JSON.stringify({ actionType: `action${i}`, timestamp: "2026-01-01T00:00:00Z" }))
        .join("\n");

      mockReadFileSync.mockReturnValue(entries + "\n");

      const logger = new AuditLogger(squadId);
      const logs = logger.getRecentLogs(10);

      expect(logs).toHaveLength(10);
    });
  });

  describe("searchLogs", () => {
    it("searches by query text", () => {
      mockReadFileSync.mockReturnValue(
        JSON.stringify({ actionType: "approved_action", timestamp: "2026-01-01T00:00:00Z", decision: "APPROVED" }) + "\n" +
        JSON.stringify({ actionType: "rejected_action", timestamp: "2026-01-01T00:01:00Z", decision: "REJECTED" }) + "\n"
      );
      mockReaddirSync.mockReturnValue([]);

      const logger = new AuditLogger(squadId);
      const results = logger.searchLogs({ query: "approved" });

      expect(results).toHaveLength(1);
      expect(results[0].actionType).toBe("approved_action");
    });

    it("filters by date range", () => {
      mockReadFileSync.mockReturnValue(
        JSON.stringify({ actionType: "action1", timestamp: "2026-01-01T00:00:00Z" }) + "\n" +
        JSON.stringify({ actionType: "action2", timestamp: "2026-01-15T00:00:00Z" }) + "\n" +
        JSON.stringify({ actionType: "action3", timestamp: "2026-02-01T00:00:00Z" }) + "\n"
      );
      mockReaddirSync.mockReturnValue([]);

      const logger = new AuditLogger(squadId);
      const results = logger.searchLogs({
        from: "2026-01-10",
        to: "2026-01-20",
      });

      expect(results).toHaveLength(1);
      expect(results[0].actionType).toBe("action2");
    });

    it("filters by claw role", () => {
      mockReadFileSync.mockReturnValue(
        JSON.stringify({ actionType: "action1", timestamp: "2026-01-01T00:00:00Z", clawRole: "content" }) + "\n" +
        JSON.stringify({ actionType: "action2", timestamp: "2026-01-01T00:01:00Z", clawRole: "finance" }) + "\n"
      );
      mockReaddirSync.mockReturnValue([]);

      const logger = new AuditLogger(squadId);
      const results = logger.searchLogs({ clawRole: "finance" });

      expect(results).toHaveLength(1);
      expect(results[0].clawRole).toBe("finance");
    });

    it("filters by decision", () => {
      mockReadFileSync.mockReturnValue(
        JSON.stringify({ actionType: "action1", timestamp: "2026-01-01T00:00:00Z", decision: "APPROVED" }) + "\n" +
        JSON.stringify({ actionType: "action2", timestamp: "2026-01-01T00:01:00Z", decision: "REJECTED" }) + "\n"
      );
      mockReaddirSync.mockReturnValue([]);

      const logger = new AuditLogger(squadId);
      const results = logger.searchLogs({ decision: "APPROVED" });

      expect(results).toHaveLength(1);
    });
  });

  describe("getRotatedLogs", () => {
    it("returns list of rotated log files", () => {
      mockReaddirSync.mockReturnValue([
        "warroom-2026-01-01.log.gz",
        "warroom-2026-01-02.log.gz",
        "warroom.log",
      ]);

      const logger = new AuditLogger(squadId);
      const files = logger.getRotatedLogs();

      expect(files).toHaveLength(2);
      expect(files).toContain("warroom-2026-01-01.log.gz");
    });
  });
});
