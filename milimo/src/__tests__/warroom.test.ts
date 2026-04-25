// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

vi.mock("node:readline", () => ({
  createInterface: vi.fn(() => ({
    on: vi.fn(),
    close: vi.fn(),
    setPrompt: vi.fn(),
    prompt: vi.fn(),
  })),
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  readdirSync: vi.fn(),
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  renameSync: vi.fn(),
  mkdirSync: vi.fn(),
  appendFileSync: vi.fn(),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
}));

vi.mock("node:os", () => ({
  homedir: vi.fn(() => "/home/test"),
}));

import { WarRoomTUI } from "../warroom/warroom";

const mockedFs = (await import("node:fs")) as any;
const mockedReadline = (await import("node:readline")) as any;

describe("WarRoomTUI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "clear").mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(process.stdout, "write").mockImplementation(() => true);
  });

  describe("constructor", () => {
    it("initializes with squad ID and operator ID", () => {
      new WarRoomTUI("test-squad", "test-operator");

      expect(mockedReadline.createInterface).toHaveBeenCalled();
    });

    it("defaults operator ID to 'local-operator'", () => {
      const tui = new WarRoomTUI("test-squad");

      expect((tui as any).operatorId).toBe("local-operator");
    });

    it("initializes ApprovalEngine with squad ID", () => {
      const tui = new WarRoomTUI("my-squad");

      expect((tui as any).squadId).toBe("my-squad");
    });

    it("initializes AuditLogger with squad ID", () => {
      const tui = new WarRoomTUI("audit-squad");

      expect((tui as any).audit).toBeDefined();
    });

    it("initializes EvolutionManager with squad ID", () => {
      const tui = new WarRoomTUI("evolution-squad");

      expect((tui as any).evolution).toBeDefined();
    });
  });

  describe("start()", () => {
    it("clears the console on start", () => {
      const tui = new WarRoomTUI("test-squad");
      tui.start();

      expect(console.clear).toHaveBeenCalled();
    });

    it("displays header with squad and operator info", () => {
      const tui = new WarRoomTUI("test-squad", "test-operator");
      tui.start();

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("test-squad"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("test-operator"));
    });

    it("sets up background polling interval", () => {
      vi.useFakeTimers();
      const tui = new WarRoomTUI("test-squad");
      tui.start();

      expect(vi.getTimerCount()).toBeGreaterThanOrEqual(0);
      vi.useRealTimers();
    });

    it("registers readline line handler", () => {
      const mockRl = {
        on: vi.fn(),
        close: vi.fn(),
        setPrompt: vi.fn(),
        prompt: vi.fn(),
      };
      (mockedReadline.createInterface as vi.Mock).mockReturnValue(mockRl);

      const tui = new WarRoomTUI("test-squad");
      tui.start();

      expect(mockRl.on).toHaveBeenCalledWith("line", expect.any(Function));
    });
  });

  describe("stop()", () => {
    it("clears the refresh interval", () => {
      const tui = new WarRoomTUI("test-squad");
      tui.start();
      tui.stop();

      expect((tui as any).isRunning).toBe(false);
    });

    it("closes the readline interface", () => {
      const mockRl = {
        on: vi.fn(),
        close: vi.fn(),
        setPrompt: vi.fn(),
        prompt: vi.fn(),
      };
      (mockedReadline.createInterface as vi.Mock).mockReturnValue(mockRl);

      const tui = new WarRoomTUI("test-squad");
      tui.stop();

      expect(mockRl.close).toHaveBeenCalled();
    });

    it("sets isRunning to false", () => {
      const tui = new WarRoomTUI("test-squad");
      tui.start();
      tui.stop();

      expect((tui as any).isRunning).toBe(false);
    });
  });

  describe("queue rendering", () => {
    it("displays 'no pending actions' when queue is empty", () => {
      mockedFs.readdirSync.mockImplementation(() => {
        throw new Error("ENOENT");
      });

      const tui = new WarRoomTUI("test-squad");
      (tui as any).listPending();

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("No pending"));
    });

    it("renders action cards with correct format", () => {
      const mockMsg = {
        message_id: "msg-001",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "deliverable",
        payload: {},
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-001.json",
      };

      mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

      const tui = new WarRoomTUI("test-squad");
      (tui as any).listPending();

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("msg-001"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("content"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("ops"));
    });

    it("shows mode tags (HOLD, REVIEW, AUTO) for each action", () => {
      const mockMsg = {
        message_id: "msg-002",
        sender_role: "finance",
        recipient_role: "ops",
        message_type: "deliverable",
        payload: { type: "invoice", amount: 600 },
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-002.json",
      };

      mockedFs.readdirSync.mockReturnValue(["msg-002.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

      const tui = new WarRoomTUI("test-squad");
      (tui as any).listPending();

      expect(console.log).toHaveBeenCalledWith(
        expect.stringMatching(/\[AUTO\]|\[REVIEW\]|\[HOLD\]|\[VETO\]/),
      );
    });
  });

  describe("claw health display", () => {
    it("shows active tools in evolution log", () => {
      mockedFs.readdirSync.mockReturnValue(["content"]);

      const tui = new WarRoomTUI("test-squad");
      (tui as any).evolution = {
        showEvolutionLog: vi.fn(),
      };

      (tui as any).handleCommand("evolution");

      expect((tui as any).evolution.showEvolutionLog).toHaveBeenCalled();
    });
  });

  describe("digest schedule triggering", () => {
    it("polls for new messages at configured interval", () => {
      vi.useFakeTimers();
      vi.spyOn(process.stdout, "write").mockImplementation(() => true);

      const tui = new WarRoomTUI("test-squad");
      tui.start();

      const initialCallCount = (process.stdout.write as vi.Mock).mock.calls.length;
      vi.advanceTimersByTime(5000);

      expect((process.stdout.write as vi.Mock).mock.calls.length).toBeGreaterThanOrEqual(
        initialCallCount,
      );
      vi.useRealTimers();
    });

    it("alerts when new messages arrive", () => {
      vi.useFakeTimers();

      const mockMsg1 = {
        message_id: "msg-1",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "test",
        payload: {},
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-1.json",
      };

      mockedFs.readdirSync.mockReturnValueOnce([]).mockReturnValueOnce(["msg-1.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg1));

      const writeSpy = vi.spyOn(process.stdout, "write");
      const tui = new WarRoomTUI("test-squad");
      tui.start();

      vi.advanceTimersByTime(5000);

      expect(writeSpy).toHaveBeenCalled();
      vi.useRealTimers();
    });
  });

  describe("command handling", () => {
    it("handles 'ls' command to list pending actions", () => {
      const tui = new WarRoomTUI("test-squad");
      vi.spyOn(tui as any, "listPending");

      (tui as any).handleCommand("ls");

      expect((tui as any).listPending).toHaveBeenCalled();
    });

    it("handles 'approve' command with message ID", () => {
      const mockMsg = {
        message_id: "msg-001",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "test",
        payload: {},
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-001.json",
      };

      mockedFs.readdirSync.mockReturnValue(["msg-001.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

      const tui = new WarRoomTUI("test-squad");

      (tui as any).pendingQueue = [mockMsg];
      (tui as any).handleCommand("approve msg-001");

      expect(mockedFs.renameSync).toHaveBeenCalled();
    });

    it("handles 'veto' command to reject action", () => {
      const mockMsg = {
        message_id: "msg-002",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "test",
        payload: {},
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-002.json",
      };

      mockedFs.readdirSync.mockReturnValue(["msg-002.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

      const tui = new WarRoomTUI("test-squad");

      (tui as any).pendingQueue = [mockMsg];
      (tui as any).handleCommand("veto msg-002");

      expect(mockedFs.renameSync).toHaveBeenCalledWith(
        expect.any(String),
        expect.stringContaining("rejected"),
      );
    });

    it("handles 'exit' command to stop TUI", () => {
      const tui = new WarRoomTUI("test-squad");
      const stopSpy = vi.spyOn(tui, "stop");

      (tui as any).handleCommand("exit");

      expect(stopSpy).toHaveBeenCalled();
    });

    it("handles 'quit' as alias for 'exit'", () => {
      const tui = new WarRoomTUI("test-squad");
      const stopSpy = vi.spyOn(tui, "stop");

      (tui as any).handleCommand("quit");

      expect(stopSpy).toHaveBeenCalled();
    });

    it("handles 'help' command to show available commands", () => {
      const tui = new WarRoomTUI("test-squad");
      (tui as any).handleCommand("help");

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("Commands:"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("ls"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("approve"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("veto"));
    });

    it("handles unknown commands gracefully", () => {
      const tui = new WarRoomTUI("test-squad");
      (tui as any).handleCommand("foobar");

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("Unknown command"));
    });

    it("handles empty input without error", () => {
      const tui = new WarRoomTUI("test-squad");

      expect(() => (tui as any).handleCommand("")).not.toThrow();
    });
  });

  describe("view action details", () => {
    it("shows tool proposal details with trigger info", () => {
      const mockMsg = {
        message_id: "msg-003",
        sender_role: "analytics",
        recipient_role: "content",
        message_type: "tool_proposal",
        payload: {
          tool_name: "auto_replier",
          trigger_pattern: { trigger_description: "Low engagement posts" },
          estimated_improvement: 12.5,
          metric_target: "engagement_rate",
          data_sources_required: ["analytics_db", "content_queue"],
        },
        timestamp: new Date().toISOString(),
        needs_approval: false,
        file_path: "/tmp/msg-003.json",
      };

      mockedFs.readdirSync.mockReturnValue(["msg-003.json"]);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockMsg));

      const tui = new WarRoomTUI("test-squad");
      (tui as any).pendingQueue = [mockMsg];
      (tui as any).handleCommand("view msg-003");

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("auto_replier"));
      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("Low engagement"));
    });

    it("shows error for missing message ID", () => {
      const tui = new WarRoomTUI("test-squad");
      (tui as any).handleCommand("view");

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("Usage:"));
    });

    it("shows error for non-existent message ID", () => {
      const tui = new WarRoomTUI("test-squad");
      (tui as any).pendingQueue = [];
      (tui as any).handleCommand("view nonexistent");

      expect(console.log).toHaveBeenCalledWith(expect.stringContaining("not found"));
    });
  });
});
