// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for ApprovalEngine
 */

import * as fs from "node:fs";
import * as path from "node:path";

jest.mock("node:fs", () => ({
  existsSync: jest.fn(),
  readdirSync: jest.fn(),
  readFileSync: jest.fn(),
  renameSync: jest.fn(),
  unlinkSync: jest.fn(),
  mkdirSync: jest.fn(),
  appendFileSync: jest.fn(),
  writeFileSync: jest.fn(),
  statSync: jest.fn(() => ({ mtime: new Date() })),
}));

jest.mock("node:path", () => ({
	join: jest.fn((...args: string[]) => args.join("/")),
}));

jest.mock("node:os", () => ({
	homedir: jest.fn(() => "/home/test"),
}));

jest.mock("yaml", () => ({
	parse: jest.fn(),
}));

import { ApprovalEngine, ApprovalMode, PendingMessage } from "../warroom/approval";
import { AuditLogger } from "../warroom/audit";
import { RateLimiter, Tier } from "../warroom/rate-limiter";

const mockedFs = jest.requireMock("node:fs");
const mockedYaml = jest.requireMock("yaml");

// Helper function defined at module level for use across describe blocks
const createMockMessage = (overrides: Partial<PendingMessage> = {}): PendingMessage => ({
  message_id: "msg-001",
  sender_role: "content",
  recipient_role: "ops",
  message_type: "deliverable",
  payload: {},
  squad_id: "test-squad",
  timestamp: new Date().toISOString(),
  needs_approval: false,
  file_path: "/home/test/.milimo/mesh/inbox/war_room/msg-001.json",
  ...overrides,
});

describe("ApprovalEngine", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedYaml.parse.mockReturnValue({ escalation_rules: [] });
    mockedFs.statSync.mockReturnValue({ mtime: new Date() } as any);
  });

	describe("getPendingMessages()", () => {
		it("returns empty array when inbox directory does not exist", () => {
			mockedFs.readdirSync.mockImplementation(() => {
				throw new Error("ENOENT");
			});

			const engine = new ApprovalEngine("test-squad");
			const messages = engine.getPendingMessages();

			expect(messages).toEqual([]);
		});

		it("returns parsed messages from inbox", () => {
			const mockMsg = createMockMessage();
			mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

			const engine = new ApprovalEngine("test-squad");
			const messages = engine.getPendingMessages();

			expect(messages).toHaveLength(1);
			expect(messages[0].message_id).toBe("msg-001");
		});

		it("sorts messages by timestamp (oldest first)", () => {
			const msgOlder = createMockMessage({ message_id: "msg-older", timestamp: "2026-03-20T09:00:00Z" });
			const msgNewer = createMockMessage({ message_id: "msg-newer", timestamp: "2026-03-20T10:00:00Z" });

			mockedFs.readdirSync.mockReturnValue(["msg-older.json", "msg-newer.json"]);
			mockedFs.readFileSync
				.mockReturnValueOnce(JSON.stringify(msgOlder))
				.mockReturnValueOnce(JSON.stringify(msgNewer));

			const engine = new ApprovalEngine("test-squad");
			const messages = engine.getPendingMessages();

			expect(messages[0].message_id).toBe("msg-older");
			expect(messages[1].message_id).toBe("msg-newer");
		});

		it("filters non-JSON files from inbox", () => {
			mockedFs.readdirSync.mockReturnValue(["msg-001.json", "readme.txt", ".hidden"]);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify(createMockMessage()));

			const engine = new ApprovalEngine("test-squad");
			const messages = engine.getPendingMessages();

			expect(messages).toHaveLength(1);
		});

		it("handles malformed JSON gracefully", () => {
			mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
			mockedFs.readFileSync.mockReturnValue("not valid json");

			const engine = new ApprovalEngine("test-squad");
			const messages = engine.getPendingMessages();

			expect(messages).toEqual([]);
		});
	});

	describe("evaluateAction()", () => {
		it("returns AUTO for messages without needs_approval flag", () => {
			const msg = createMockMessage({ needs_approval: false });
			const engine = new ApprovalEngine("test-squad");

			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("AUTO");
		});

		it("returns REVIEW for messages with needs_approval=true", () => {
			const msg = createMockMessage({ needs_approval: true });
			const engine = new ApprovalEngine("test-squad");

			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("REVIEW");
		});

  it("returns VETO for invoice over $500 (escalation rule)", () => {
    const msg = createMockMessage({
      message_type: "deliverable",
      payload: { type: "invoice", amount: 600 },
    });

    mockedFs.existsSync.mockReturnValue(true);
    mockedFs.readFileSync.mockReturnValue("mock yaml");
    mockedYaml.parse.mockReturnValue({
      escalation_rules: [
        { trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
      ],
    });

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("VETO");
    expect(result.trigger).toBe("invoice_over_500");
  });

  it("returns AUTO for invoice exactly $500 (edge case)", () => {
    const msg = createMockMessage({
      message_type: "deliverable",
      payload: { type: "invoice", amount: 500 },
    });

    mockedFs.existsSync.mockReturnValue(true);
    mockedFs.readFileSync.mockReturnValue("mock yaml");
    mockedYaml.parse.mockReturnValue({
      escalation_rules: [
        { trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
      ],
    });

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("AUTO");
  });

  it("applies HOLD escalation for specific triggers", () => {
    const msg = createMockMessage({
      message_type: "deliverable",
      payload: { type: "invoice", amount: 1000 },
    });

    // Mock for constructor's loadEscalationRules
    mockedFs.existsSync.mockReturnValue(true);
    mockedFs.readFileSync.mockReturnValue("mock yaml content");
    mockedYaml.parse.mockReturnValue({
      escalation_rules: [
        { trigger: "invoice_over_500", action: "HOLD", description: "Review needed" },
      ],
    });

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("HOLD");
  });
});

describe("priority ordering (HOLD > REVIEW > AUTO)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedFs.statSync.mockReturnValue({ mtime: new Date() } as any);
  });

  it("escalation rules take highest priority", () => {
    const msg = createMockMessage({
      message_type: "deliverable",
      payload: { type: "invoice", amount: 800 },
    });

    mockedFs.existsSync.mockReturnValue(true);
    mockedFs.readFileSync.mockReturnValue("mock yaml content");
    mockedYaml.parse.mockReturnValue({
      escalation_rules: [
        { trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
      ],
    });

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("VETO");
  });

  it("needs_approval flag triggers REVIEW when no escalation", () => {
    const msg = createMockMessage({ needs_approval: true });
    mockedFs.existsSync.mockReturnValue(false);

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("REVIEW");
  });

  it("AUTO is the default fallback", () => {
    const msg = createMockMessage({ needs_approval: false });
    mockedFs.existsSync.mockReturnValue(false);

    const engine = new ApprovalEngine("test-squad");
    const result = engine.evaluateAction(msg);

    expect(result.mode).toBe("AUTO");
  });
});
});
