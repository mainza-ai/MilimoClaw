// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for RealtimeBridge
 */

import { EventEmitter } from "node:events";
import { RealtimeBridge, type RealtimeEvent, type ActionQueuedEvent } from "../warroom/realtime-bridge";

const mockWss = {
  on: jest.fn(),
  close: jest.fn(),
};

const mockServer = {
  listen: jest.fn((port, cb) => cb?.()),
  close: jest.fn(),
};

jest.mock("node:http", () => ({
  createServer: jest.fn(() => mockServer),
}));

jest.mock("ws", () => ({
  WebSocketServer: jest.fn(() => mockWss),
  WebSocket: {
    OPEN: 1,
  },
}));

jest.mock("node:fs", () => ({
  existsSync: jest.fn(() => false),
  readdirSync: jest.fn(() => []),
  readFileSync: jest.fn(),
  watch: jest.fn(() => ({ close: jest.fn() })),
}));

const mockedFs = jest.requireMock("node:fs");

describe("RealtimeBridge", () => {
  const defaultOptions = {
    port: 9876,
    squadId: "test-squad",
    blueprintDir: "/tmp/test",
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockWss.on.mockClear();
    mockServer.listen.mockClear();
  });

  describe("constructor", () => {
    it("initializes with default port 9876", () => {
      const bridge = new RealtimeBridge({ squadId: "test", blueprintDir: "/tmp" });

      expect((bridge as unknown as { port: number }).port).toBe(9876);
    });

    it("accepts custom port", () => {
      const bridge = new RealtimeBridge({
        port: 9999,
        squadId: "test",
        blueprintDir: "/tmp",
      });

      expect((bridge as unknown as { port: number }).port).toBe(9999);
    });

    it("initializes not running", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      expect(bridge.isRunning()).toBe(false);
    });
  });

  describe("start", () => {
    it("creates HTTP server and WebSocket server", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      bridge.start();

      expect(mockServer.listen).toHaveBeenCalledWith(9876, expect.any(Function));
      expect(mockWss.on).toHaveBeenCalledWith("connection", expect.any(Function));
    });

    it("sets running to true after start", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      bridge.start();

      expect(bridge.isRunning()).toBe(true);
    });

    it("does not start twice", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      bridge.start();
      bridge.start();

      expect(mockServer.listen).toHaveBeenCalledTimes(1);
    });
  });

  describe("stop", () => {
    it("closes server and WebSocket server", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      bridge.start();
      bridge.stop();

      expect(mockWss.close).toHaveBeenCalled();
      expect(mockServer.close).toHaveBeenCalled();
    });

    it("sets running to false after stop", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      bridge.start();
      bridge.stop();

      expect(bridge.isRunning()).toBe(false);
    });
  });

  describe("event handlers", () => {
    it("registers action handler", () => {
      const bridge = new RealtimeBridge(defaultOptions);
      const handler = jest.fn();

      bridge.onAction(handler);

      expect((bridge as unknown as { actionHandlers: unknown[] }).actionHandlers).toContain(handler);
    });

    it("registers status handler", () => {
      const bridge = new RealtimeBridge(defaultOptions);
      const handler = jest.fn();

      bridge.onHealthUpdate(handler);

      expect((bridge as unknown as { statusHandlers: unknown[] }).statusHandlers).toContain(handler);
    });

    it("registers evolution handler", () => {
      const bridge = new RealtimeBridge(defaultOptions);
      const handler = jest.fn();

      bridge.onEvolutionEvent(handler);

      expect((bridge as unknown as { evolutionHandlers: unknown[] }).evolutionHandlers).toContain(handler);
    });

    it("registers revenue handler", () => {
      const bridge = new RealtimeBridge(defaultOptions);
      const handler = jest.fn();

      bridge.onRevenueUpdate(handler);

      expect((bridge as unknown as { revenueHandlers: unknown[] }).revenueHandlers).toContain(handler);
    });
  });

  describe("broadcast", () => {
    it("sends message to all connected clients", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      const mockClient1 = {
        readyState: 1,
        send: jest.fn(),
      };

      const mockClient2 = {
        readyState: 1,
        send: jest.fn(),
      };

      (bridge as unknown as { clients: Set<{ readyState: number; send: jest.Mock }> }).clients.add(mockClient1 as unknown as { readyState: number; send: jest.Mock });
      (bridge as unknown as { clients: Set<{ readyState: number; send: jest.Mock }> }).clients.add(mockClient2 as unknown as { readyState: number; send: jest.Mock });

      const event: RealtimeEvent = {
        type: "action_queued",
        timestamp: "2026-03-20T10:00:00Z",
        data: {
          action_id: "act_123",
          claw: "content",
          action_type: "tool_proposal",
          priority: "REVIEW",
          message_type: "tool_proposal",
          payload: {},
        },
      };

      bridge.broadcast(event);

      expect(mockClient1.send).toHaveBeenCalledWith(JSON.stringify(event));
      expect(mockClient2.send).toHaveBeenCalledWith(JSON.stringify(event));
    });

    it("skips clients that are not open", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      const mockClient1 = {
        readyState: 1,
        send: jest.fn(),
      };

      const mockClient2 = {
        readyState: 0,
        send: jest.fn(),
      };

      (bridge as unknown as { clients: Set<{ readyState: number; send: jest.Mock }> }).clients.add(mockClient1 as unknown as { readyState: number; send: jest.Mock });
      (bridge as unknown as { clients: Set<{ readyState: number; send: jest.Mock }> }).clients.add(mockClient2 as unknown as { readyState: number; send: jest.Mock });

      const event: RealtimeEvent = {
        type: "action_queued",
        timestamp: "2026-03-20T10:00:00Z",
        data: {
          action_id: "act_123",
          claw: "content",
          action_type: "tool_proposal",
          priority: "REVIEW",
          message_type: "tool_proposal",
          payload: {},
        },
      };

      bridge.broadcast(event);

      expect(mockClient1.send).toHaveBeenCalled();
      expect(mockClient2.send).not.toHaveBeenCalled();
    });
  });

  describe("getConnectedClients", () => {
    it("returns number of connected clients", () => {
      const bridge = new RealtimeBridge(defaultOptions);

      expect(bridge.getConnectedClients()).toBe(0);

      (bridge as unknown as { clients: Set<number> }).clients.add(1 as unknown as never);
      expect(bridge.getConnectedClients()).toBe(1);
    });
  });
});
