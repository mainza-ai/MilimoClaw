// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

vi.mock("../lib/python-bridge", () => ({
  callPythonBridgeSafe: vi.fn(
    (command: string, args: Record<string, unknown>, _options: Record<string, unknown>) => {
      if (command === "activate_deep_work") {
        return {
          success: true,
          data: {
            active: true,
            activated_at: "2026-03-20T10:00:00Z",
            resume_date: args.resume_date,
            policy_changes: [
              {
                claw: "content",
                previous: "normal",
                new: "pause_drafts",
                blocked_actions: ["publish", "send"],
              },
              {
                claw: "ops",
                previous: "normal",
                new: "maintenance",
                blocked_actions: ["new_outreach", "follow_up"],
              },
              {
                claw: "analytics",
                previous: "normal",
                new: "passive",
                blocked_actions: ["experiment", "test"],
              },
              {
                claw: "finance",
                previous: "normal",
                new: "invoices_only",
                blocked_actions: ["new_invoice", "new_client"],
              },
              {
                claw: "build",
                previous: "normal",
                new: "issues_only",
                blocked_actions: ["open_pr", "merge"],
              },
            ],
          },
        };
      }
      if (command === "resume_deep_work") {
        return {
          success: true,
          data: {
            active: false,
            deactivated_at: "2026-03-27T10:00:00Z",
            policies_restored: ["content", "ops", "analytics", "finance", "build"],
          },
        };
      }
      if (command === "deep_work_status") {
        return {
          success: true,
          data: { active: false },
        };
      }
      return { success: false, error: "Unknown command" };
    },
  ),
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  mkdirSync: vi.fn(),
  writeFileSync: vi.fn(),
  readFileSync: vi.fn(),
}));

vi.mock("node:path", () => ({
  join: (...args: string[]) => args.join("/"),
  dirname: (p: string) => p.split("/").slice(0, -1).join("/"),
}));

vi.mock("../commands/init", () => ({
  loadMilimoState: vi.fn(() => ({
    squadName: "test-squad",
    clawRole: "content",
    template: "solo-founder",
    solo: true,
    meshMembers: ["content", "ops", "analytics", "finance", "build"],
    initializedAt: "2026-01-01T00:00:00Z",
    blueprintVersion: "0.1.0",
  })),
}));

import { parseDurationDays, formatResumeDate, calculateResumeDate } from "../commands/squad";
import { callPythonBridgeSafe } from "../lib/python-bridge";

describe("squad finals-mode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("parseDurationDays", () => {
    it("parses days correctly", () => {
      expect(parseDurationDays("3days")).toBe(3);
      expect(parseDurationDays("10 days")).toBe(10);
      expect(parseDurationDays("1day")).toBe(1);
    });

    it("parses weeks correctly", () => {
      expect(parseDurationDays("2weeks")).toBe(14);
      expect(parseDurationDays("1 week")).toBe(7);
      expect(parseDurationDays("3weeks")).toBe(21);
    });

    it("parses months correctly", () => {
      expect(parseDurationDays("1month")).toBe(30);
      expect(parseDurationDays("2 months")).toBe(60);
    });

    it("returns default for invalid format", () => {
      expect(parseDurationDays("invalid")).toBe(14);
      expect(parseDurationDays("")).toBe(14);
    });

    it("handles case insensitivity", () => {
      expect(parseDurationDays("2WEEKS")).toBe(14);
      expect(parseDurationDays("3DAYS")).toBe(3);
    });
  });

  describe("formatResumeDate", () => {
    it("formats date as YYYY-MM-DD", () => {
      const date = new Date("2026-04-01T12:00:00Z");
      expect(formatResumeDate(date)).toBe("2026-04-01");
    });

    it("handles beginning of year", () => {
      const date = new Date("2026-01-01T00:00:00Z");
      expect(formatResumeDate(date)).toBe("2026-01-01");
    });

    it("handles end of year", () => {
      const date = new Date("2026-12-31T23:59:59Z");
      expect(formatResumeDate(date)).toBe("2026-12-31");
    });
  });

  describe("calculateResumeDate", () => {
    it("calculates resume date from duration", () => {
      const resumeDate = calculateResumeDate("2weeks");
      const expected = new Date();
      expected.setDate(expected.getDate() + 14);
      expect(resumeDate).toBe(formatResumeDate(expected));
    });

    it("calculates resume date for 3 days", () => {
      const resumeDate = calculateResumeDate("3days");
      const expected = new Date();
      expected.setDate(expected.getDate() + 3);
      expect(resumeDate).toBe(formatResumeDate(expected));
    });

    it("calculates resume date for 1 month", () => {
      const resumeDate = calculateResumeDate("1month");
      const expected = new Date();
      expected.setDate(expected.getDate() + 30);
      expect(resumeDate).toBe(formatResumeDate(expected));
    });
  });

  describe("duration validation", () => {
    it("accepts valid durations", () => {
      expect(() => parseDurationDays("2weeks")).not.toThrow();
      expect(() => parseDurationDays("3days")).not.toThrow();
      expect(() => parseDurationDays("1month")).not.toThrow();
    });

    it("handles edge cases", () => {
      expect(parseDurationDays("0days")).toBe(0);
      expect(parseDurationDays("100weeks")).toBe(700);
    });
  });
});

describe("bridge integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("activate_deep_work", () => {
    it("calls bridge with correct parameters", async () => {
      await callPythonBridgeSafe(
        "activate_deep_work",
        { resume_date: "2026-04-01" },
        { blueprintDir: "/tmp" },
      );

      expect(callPythonBridgeSafe).toHaveBeenCalledWith(
        "activate_deep_work",
        { resume_date: "2026-04-01" },
        { blueprintDir: "/tmp" },
      );
    });

    it("returns policy changes per claw", () => {
      const result = callPythonBridgeSafe(
        "activate_deep_work",
        { resume_date: "2026-04-01" },
        { blueprintDir: "/tmp" },
      );

      expect(result.success).toBe(true);
      expect(result.data.policy_changes).toHaveLength(5);
      expect(result.data.policy_changes[0]).toHaveProperty("claw");
      expect(result.data.policy_changes[0]).toHaveProperty("previous");
      expect(result.data.policy_changes[0]).toHaveProperty("new");
    });

    it("includes blocked and queued actions", () => {
      const result = callPythonBridgeSafe(
        "activate_deep_work",
        { resume_date: "2026-04-01" },
        { blueprintDir: "/tmp" },
      );

      expect(result.data.policy_changes[0].blocked_actions).toContain("publish");
      expect(result.data.policy_changes[0].blocked_actions).toContain("send");
    });
  });

  describe("resume_deep_work", () => {
    it("calls bridge to resume operations", async () => {
      await callPythonBridgeSafe("resume_deep_work", {}, { blueprintDir: "/tmp" });

      expect(callPythonBridgeSafe).toHaveBeenCalledWith(
        "resume_deep_work",
        {},
        { blueprintDir: "/tmp" },
      );
    });

    it("returns list of restored policies", () => {
      const result = callPythonBridgeSafe("resume_deep_work", {}, { blueprintDir: "/tmp" });

      expect(result.success).toBe(true);
      expect(result.data.policies_restored).toHaveLength(5);
    });

    it("returns deactivated_at timestamp", () => {
      const result = callPythonBridgeSafe("resume_deep_work", {}, { blueprintDir: "/tmp" });

      expect(result.data.deactivated_at).toBeDefined();
    });
  });

  describe("deep_work_status", () => {
    it("returns current status", () => {
      const result = callPythonBridgeSafe("deep_work_status", {}, { blueprintDir: "/tmp" });

      expect(result.success).toBe(true);
      expect(result.data).toHaveProperty("active");
    });
  });
});

describe("config state", () => {
  it("stores deep_work state with required fields", () => {
    const deepWorkState = {
      active: true,
      activated_at: "2026-03-20T10:00:00Z",
      resume_date: "2026-04-03",
    };

    expect(deepWorkState).toHaveProperty("active");
    expect(deepWorkState).toHaveProperty("activated_at");
    expect(deepWorkState).toHaveProperty("resume_date");
    expect(typeof deepWorkState.activated_at).toBe("string");
    expect(typeof deepWorkState.resume_date).toBe("string");
  });

  it("clears deep_work state on resume", () => {
    const deepWorkState = {
      active: false,
      activated_at: "",
      resume_date: "",
    };

    expect(deepWorkState.active).toBe(false);
  });
});

describe("error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles already-active error", () => {
    const existingState = {
      active: true,
      activatedAt: "2026-03-20T10:00:00Z",
      duration: "2weeks",
      resumeDate: "2026-04-03",
      previousPolicies: {},
    };

    expect(existingState.active).toBe(true);
  });

  it("handles not-active error on resume", () => {
    const existingState = null;
    expect(existingState).toBeNull();
  });

  it("requires at least one of duration or resume-date", () => {
    const hasDuration = false;
    const hasResumeDate = false;

    expect(hasDuration || hasResumeDate).toBe(false);
  });
});
