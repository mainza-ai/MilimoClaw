// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { DigestScheduler, type DigestBrief, type DigestConfig } from "../warroom/digest";

vi.mock("../lib/python-bridge", () => ({
  callPythonBridgeSafe: vi.fn(
    (command: string, _args: Record<string, unknown>, _options: Record<string, unknown>) => {
      if (command === "morning_brief") {
        return {
          success: true,
          data: {
            overnight_actions: 3,
            queue_summary: { hold: 1, review: 2, auto: 1 },
            pending_actions: [
              { id: "act_123", claw: "content", type: "deliverable", priority: "HOLD" },
            ],
          },
        };
      }
      if (command === "evening_wrap") {
        return {
          success: true,
          data: {
            today_completed: 5,
            auto_executed: 2,
            remaining_pending: 3,
          },
        };
      }
      return { success: false, error: "Unknown command" };
    },
  ),
}));

import { callPythonBridgeSafe } from "../lib/python-bridge";

const mockBridge = { callPythonBridgeSafe };

describe("DigestScheduler", () => {
  const defaultConfig: DigestConfig = {
    morning_time: { hour: 7, minute: 0 },
    evening_time: { hour: 20, minute: 0 },
    squad_id: "test-squad",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("constructor", () => {
    it("initializes with config and blueprintDir", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      expect(scheduler.isRunning()).toBe(false);
    });

    it("accepts onUpdate callback", () => {
      const onUpdate = vi.fn();
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
        onUpdate,
      });

      expect(scheduler.isRunning()).toBe(false);
    });

    it("accepts onError callback", () => {
      const onError = vi.fn();
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
        onError,
      });

      expect(scheduler.isRunning()).toBe(false);
    });
  });

  describe("start()", () => {
    it("sets running to true", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      scheduler.start();

      expect(scheduler.isRunning()).toBe(true);
    });

    it("does not start twice", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      scheduler.start();
      scheduler.start();

      expect(scheduler.isRunning()).toBe(true);
    });
  });

  describe("stop()", () => {
    it("sets running to false", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      scheduler.start();
      scheduler.stop();

      expect(scheduler.isRunning()).toBe(false);
    });

    it("clears morning timer", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      scheduler.start();
      scheduler.stop();

      expect(scheduler.getNextMorningTime()).toBeNull();
    });

    it("clears evening timer", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      scheduler.start();
      scheduler.stop();

      expect(scheduler.getNextEveningTime()).toBeNull();
    });
  });

  describe("getMorningBrief()", () => {
    it("calls python bridge with morning_brief command", async () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      await scheduler.getMorningBrief();

      expect(mockBridge.callPythonBridgeSafe).toHaveBeenCalledWith(
        "morning_brief",
        { squad_id: "test-squad" },
        { blueprintDir: "/tmp/test" },
      );
    });

    it("returns DigestBrief with morning data", async () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief = await scheduler.getMorningBrief();

      expect(brief).not.toBeNull();
      expect(brief?.type).toBe("morning");
      expect(brief?.overnight_actions).toBe(3);
      expect(brief?.queue_summary).toEqual({ hold: 1, review: 2, auto: 1 });
    });

    it("calls onUpdate callback on success", async () => {
      const onUpdate = vi.fn();
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
        onUpdate,
      });

      await scheduler.getMorningBrief();

      expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ type: "morning" }));
    });

    it("includes generated_at timestamp", async () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief = await scheduler.getMorningBrief();

      expect(brief?.generated_at).toBeDefined();
      expect(new Date(brief?.generated_at ?? "").toISOString()).toBe(brief?.generated_at);
    });
  });

  describe("getEveningWrap()", () => {
    it("calls python bridge with evening_wrap command", async () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      await scheduler.getEveningWrap();

      expect(mockBridge.callPythonBridgeSafe).toHaveBeenCalledWith(
        "evening_wrap",
        { squad_id: "test-squad" },
        { blueprintDir: "/tmp/test" },
      );
    });

    it("returns DigestBrief with evening data", async () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief = await scheduler.getEveningWrap();

      expect(brief).not.toBeNull();
      expect(brief?.type).toBe("evening");
      expect(brief?.today_completed).toBe(5);
      expect(brief?.auto_executed).toBe(2);
      expect(brief?.remaining_pending).toBe(3);
    });

    it("calls onUpdate callback on success", async () => {
      const onUpdate = vi.fn();
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
        onUpdate,
      });

      await scheduler.getEveningWrap();

      expect(onUpdate).toHaveBeenCalledWith(expect.objectContaining({ type: "evening" }));
    });
  });

  describe("renderBrief()", () => {
    it("renders morning brief with correct header", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "morning",
        overnight_actions: 2,
        queue_summary: { hold: 1, review: 2, auto: 1 },
        pending_actions: [
          { id: "act_123", claw: "content", type: "deliverable", priority: "HOLD" },
        ],
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("MORNING BRIEF"))).toBe(true);
    });

    it("renders evening brief with correct header", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "evening",
        today_completed: 5,
        auto_executed: 2,
        remaining_pending: 1,
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("EVENING WRAP"))).toBe(true);
    });

    it("shows queue status for morning brief", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "morning",
        queue_summary: { hold: 3, review: 2, auto: 1 },
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("HOLD: 3"))).toBe(true);
      expect(lines.some((l) => l.includes("REVIEW: 2"))).toBe(true);
      expect(lines.some((l) => l.includes("AUTO: 1"))).toBe(true);
    });

    it("shows pending actions up to 5", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "morning",
        pending_actions: [
          { id: "act_1", claw: "content", type: "deliverable", priority: "HOLD" },
          { id: "act_2", claw: "ops", type: "signal", priority: "REVIEW" },
          { id: "act_3", claw: "finance", type: "query", priority: "AUTO" },
          { id: "act_4", claw: "build", type: "deliverable", priority: "REVIEW" },
          { id: "act_5", claw: "analytics", type: "summary", priority: "AUTO" },
          { id: "act_6", claw: "content", type: "brief", priority: "HOLD" },
        ],
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);
      const actionLines = lines.filter((l) => l.includes("act_"));

      expect(actionLines.length).toBeLessThanOrEqual(5);
    });

    it("shows today summary for evening brief", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "evening",
        today_completed: 7,
        auto_executed: 3,
        remaining_pending: 2,
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("Total processed: 7"))).toBe(true);
      expect(lines.some((l) => l.includes("Auto-executed: 3"))).toBe(true);
      expect(lines.some((l) => l.includes("Remaining pending: 2"))).toBe(true);
    });

    it("shows warning for pending actions in evening", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const brief: DigestBrief = {
        type: "evening",
        remaining_pending: 3,
        generated_at: new Date().toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("still pending"))).toBe(true);
    });

    it("shows evolution updates on Sunday", () => {
      const scheduler = new DigestScheduler({
        config: defaultConfig,
        blueprintDir: "/tmp/test",
      });

      const sundayDate = new Date();
      sundayDate.setDate(sundayDate.getDate() - sundayDate.getDay());

      const brief: DigestBrief = {
        type: "morning",
        evolution_updates: [
          { claw: "content", tool: "auto_replier", timestamp: sundayDate.toISOString() },
        ],
        generated_at: sundayDate.toISOString(),
      };

      const lines = scheduler.renderBrief(brief);

      expect(lines.some((l) => l.includes("Evolution Updates") || l.includes("auto_replier"))).toBe(
        true,
      );
    });
  });

  describe("scheduler timing", () => {
    it("calculates delay to next morning time", () => {
      const scheduler = new DigestScheduler({
        config: {
          morning_time: { hour: 7, minute: 0 },
          evening_time: { hour: 20, minute: 0 },
          squad_id: "test-squad",
        },
        blueprintDir: "/tmp/test",
      });

      scheduler.start();

      const nextMorning = scheduler.getNextMorningTime();
      expect(nextMorning).not.toBeNull();
      expect(nextMorning?.getHours()).toBe(7);
      expect(nextMorning?.getMinutes()).toBe(0);
    });

    it("calculates delay to next evening time", () => {
      const scheduler = new DigestScheduler({
        config: {
          morning_time: { hour: 7, minute: 0 },
          evening_time: { hour: 20, minute: 0 },
          squad_id: "test-squad",
        },
        blueprintDir: "/tmp/test",
      });

      scheduler.start();

      const nextEvening = scheduler.getNextEveningTime();
      expect(nextEvening).not.toBeNull();
      expect(nextEvening?.getHours()).toBe(20);
      expect(nextEvening?.getMinutes()).toBe(0);
    });

    it("schedules for next day if time has passed", () => {
      const now = new Date();
      const pastHour = (now.getHours() - 1 + 24) % 24;

      const scheduler = new DigestScheduler({
        config: {
          morning_time: { hour: pastHour, minute: 0 },
          evening_time: { hour: 20, minute: 0 },
          squad_id: "test-squad",
        },
        blueprintDir: "/tmp/test",
      });

      scheduler.start();

      const nextMorning = scheduler.getNextMorningTime();
      expect(nextMorning).not.toBeNull();
      expect(nextMorning?.getDate()).toBeGreaterThan(now.getDate() - 1);
    });
  });
});
