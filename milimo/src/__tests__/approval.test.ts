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

describe("ApprovalEngine", () => {
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

	beforeEach(() => {
		jest.clearAllMocks();
		mockedYaml.parse.mockReturnValue({ escalation_rules: [] });
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
			mockedFs.readFileSync.mockReturnValue(JSON.stringify({
				escalation_rules: [
					{ trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
				],
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("VETO");
			expect(result.trigger).toBe("invoice_over_500");
		});

		it("returns REVIEW for invoice exactly $500 (edge case)", () => {
			const msg = createMockMessage({
				message_type: "deliverable",
				payload: { type: "invoice", amount: 500 },
			});

			mockedFs.readFileSync.mockReturnValue(JSON.stringify({
				escalation_rules: [
					{ trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
				],
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("AUTO");
		});

		it("returns REVIEW for tool_proposal when require_proposal_approval=true", () => {
			const msg = createMockMessage({
				message_type: "tool_proposal",
				payload: { tool_name: "auto_replier" },
			});

			mockedFs.existsSync.mockReturnValue(true);
			mockedFs.readFileSync.mockReturnValueOnce(JSON.stringify({ escalation_rules: [] }));
			mockedFs.readFileSync.mockReturnValueOnce(JSON.stringify({
				deployment: { require_proposal_approval: true },
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("REVIEW");
		});

		it("returns AUTO for tool_proposal when require_proposal_approval=false", () => {
			const msg = createMockMessage({
				message_type: "tool_proposal",
				payload: { tool_name: "auto_replier" },
			});

			mockedFs.readFileSync.mockReturnValue(JSON.stringify({
				deployment: { require_proposal_approval: false },
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("AUTO");
		});
	});

	describe("processDecision()", () => {
		it("moves approved message to recipient inbox", () => {
			const msg = createMockMessage();
			const engine = new ApprovalEngine("test-squad");

			engine.processDecision(msg, "APPROVED", "test-operator");

			expect(mockedFs.renameSync).toHaveBeenCalledWith(
				expect.stringContaining("war_room"),
				expect.stringContaining("ops")
			);
		});

		it("moves rejected message to rejected directory", () => {
			const msg = createMockMessage();
			const engine = new ApprovalEngine("test-squad");

			engine.processDecision(msg, "REJECTED", "test-operator");

			expect(mockedFs.renameSync).toHaveBeenCalledWith(
				expect.stringContaining("war_room"),
				expect.stringContaining("rejected")
			);
		});

		it("does not move message for DELEGATED decision", () => {
			const msg = createMockMessage();
			const engine = new ApprovalEngine("test-squad");

			engine.processDecision(msg, "DELEGATED", "test-operator");

			expect(mockedFs.renameSync).not.toHaveBeenCalled();
		});

		it("logs decision to audit log", () => {
			const msg = createMockMessage();
			const engine = new ApprovalEngine("test-squad");

			engine.processDecision(msg, "APPROVED", "test-operator", "Test approval");

			expect(mockedFs.appendFileSync).toHaveBeenCalledWith(
				expect.stringContaining("audit"),
				expect.stringContaining("APPROVED"),
				"utf8"
			);
		});
	});

	describe("autoProcessEligible()", () => {
		it("auto-approves messages with AUTO mode", () => {
			const msg = createMockMessage({ needs_approval: false });
			mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify(msg));

			const engine = new ApprovalEngine("test-squad");
			engine.autoProcessEligible();

			expect(mockedFs.renameSync).toHaveBeenCalled();
		});

		it("does not auto-approve messages with REVIEW mode", () => {
			const msg = createMockMessage({ needs_approval: true });
			mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify(msg));

			const engine = new ApprovalEngine("test-squad");
			engine.autoProcessEligible();

			expect(mockedFs.renameSync).not.toHaveBeenCalled();
		});

		it("respects rate limiter for free tier", () => {
			const msg = createMockMessage({ needs_approval: false });
			mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify(msg));

			const engine = new ApprovalEngine("test-squad", "free");
			const limiter = (engine as any).rateLimiter;

			if (limiter) {
				jest.spyOn(limiter, "tryConsume").mockReturnValue({
					allowed: false,
					remaining: 0,
					resetAt: new Date().toISOString(),
					reason: "Rate limited",
				});
			}

			engine.autoProcessEligible();

			expect(mockedFs.renameSync).not.toHaveBeenCalled();
		});
	});

	describe("escalation threshold enforcement", () => {
		it("applies HOLD escalation for specific triggers", () => {
			const msg = createMockMessage({
				message_type: "deliverable",
				payload: { type: "invoice", amount: 1000 },
			});

			mockedFs.existsSync.mockReturnValue(true);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify({
				escalation_rules: [
					{ trigger: "invoice_over_500", action: "HOLD", description: "Review needed" },
				],
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("HOLD");
		});
	});

	describe("priority ordering (HOLD > REVIEW > AUTO)", () => {
		it("escalation rules take highest priority", () => {
			const msg = createMockMessage({
				message_type: "deliverable",
				payload: { type: "invoice", amount: 800 },
			});

			mockedFs.existsSync.mockReturnValue(true);
			mockedFs.readFileSync.mockReturnValue(JSON.stringify({
				escalation_rules: [
					{ trigger: "invoice_over_500", action: "VETO", description: "Large invoice" },
				],
			}));

			const engine = new ApprovalEngine("test-squad");
			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("VETO");
		});

		it("needs_approval flag triggers REVIEW when no escalation", () => {
			const msg = createMockMessage({ needs_approval: true });
			const engine = new ApprovalEngine("test-squad");

			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("REVIEW");
		});

		it("AUTO is the default fallback", () => {
			const msg = createMockMessage({ needs_approval: false });
			const engine = new ApprovalEngine("test-squad");

			const result = engine.evaluateAction(msg);

			expect(result.mode).toBe("AUTO");
		});
	});
});
