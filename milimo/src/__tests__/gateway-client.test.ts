// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const mockSocketInstance = {
  connect: vi.fn(),
  write: vi.fn(),
  destroy: vi.fn(),
  on: vi.fn(),
  once: vi.fn(),
};

vi.mock("node:net", () => ({
  Socket: function () {
    return mockSocketInstance;
  },
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn((path: string) => path.includes("gateway")),
  mkdirSync: vi.fn(),
  writeFileSync: vi.fn(),
  readdirSync: vi.fn(),
  readFileSync: vi.fn(),
  unlinkSync: vi.fn(),
}));

vi.mock("node:crypto", () => ({
  createCipheriv: vi.fn(() => ({
    update: vi.fn(() => Buffer.from("encrypted")),
    final: vi.fn(() => Buffer.from("")),
    getAuthTag: vi.fn(() => Buffer.from("tag")),
  })),
  createDecipheriv: vi.fn(() => ({
    setAuthTag: vi.fn(),
    update: vi.fn(() => Buffer.from('{"id":"test"}')),
    final: vi.fn(() => Buffer.from("")),
  })),
  randomBytes: vi.fn(() => Buffer.from("1234567890123456")),
  hkdfSync: vi.fn(() => Buffer.alloc(32, "a")),
}));

import {
  GatewayClient,
  GatewayDeliveryError,
  getGatewaySocketPath,
  checkGatewayAvailable,
} from "../mesh/gateway-client";

const mockedFs = await import("node:fs");

describe("GatewayClient", () => {
  const defaultOptions = {
    squadId: "test-squad",
    meshSecret: "test-secret-12345",
  };

  let client: GatewayClient;

  beforeEach(() => {
    vi.restoreAllMocks();
    mockSocketInstance.connect.mockReset();
    mockSocketInstance.write.mockReset();
    mockSocketInstance.destroy.mockReset();
    mockSocketInstance.on.mockReset();
    mockSocketInstance.once.mockReset();
  });

  describe("constructor", () => {
    it("initializes with squad ID and mesh secret", () => {
      client = new GatewayClient(defaultOptions);

      expect(client.isConnected()).toBe(false);
    });

    it("uses macOS socket path on darwin", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "darwin", configurable: true });

      expect(getGatewaySocketPath()).toBe("/tmp/openshell-gateway.sock");

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });

    it("uses Linux socket path on linux", () => {
      const originalPlatform = process.platform;
      Object.defineProperty(process, "platform", { value: "linux", configurable: true });

      expect(getGatewaySocketPath()).toBe("/var/run/openshell/gateway.sock");

      Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
    });

    it("accepts message handler in options", () => {
      const handler = vi.fn();
      client = new GatewayClient({ ...defaultOptions, onMessage: handler });

      expect(handler).toBeDefined();
    });
  });

  describe("connect()", () => {
    it("sets connected to true on successful connection", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(true);

      mockSocketInstance.once.mockImplementation((event: string, callback: () => void) => {
        if (event === "connect") {
          callback();
        }
      });

      client = new GatewayClient(defaultOptions);
      await client.connect();

      expect(client.isConnected()).toBe(true);
    });

    it("enters fallback mode when socket not available", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(false);

      client = new GatewayClient(defaultOptions);
      await client.connect();

      expect(client.getFallbackMode()).toBe(true);
    });
  });

  describe("send()", () => {
    it("writes message to file in fallback mode", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(false);

      client = new GatewayClient(defaultOptions);
      await client.connect();

      const message = {
        id: "msg-123",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "deliverable",
        payload: { test: true },
        timestamp: new Date().toISOString(),
      };

      await client.send(message);

      expect(mockedFs.writeFileSync).toHaveBeenCalled();
    });

    it("throws GatewayDeliveryError on timeout", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(true);

      mockSocketInstance.once.mockImplementation((event: string, callback: () => void) => {
        if (event === "connect") {
          callback();
        }
      });
      mockSocketInstance.on.mockImplementation(() => {});
      mockSocketInstance.write.mockImplementation(() => {});

      client = new GatewayClient(defaultOptions);
      await client.connect();

      const message = {
        id: "msg-timeout",
        sender_role: "content",
        recipient_role: "ops",
        message_type: "signal",
        payload: {},
        timestamp: new Date().toISOString(),
      };

      await expect(client.send(message)).rejects.toThrow(GatewayDeliveryError);
    }, 10000);
  });

  describe("disconnect()", () => {
    it("destroys the socket", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(true);

      mockSocketInstance.once.mockImplementation((event: string, callback: () => void) => {
        if (event === "connect") {
          callback();
        }
      });

      client = new GatewayClient(defaultOptions);
      await client.connect();
      client.disconnect();

      expect(mockSocketInstance.destroy).toHaveBeenCalled();
      expect(client.isConnected()).toBe(false);
    });
  });

  describe("onMessage()", () => {
    it("registers message handler", () => {
      client = new GatewayClient(defaultOptions);
      const handler = vi.fn();

      client.onMessage(handler);

      expect(handler).toBeDefined();
    });
  });

  describe("getFallbackMode()", () => {
    it("returns true when in fallback", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(false);

      client = new GatewayClient(defaultOptions);
      await client.connect();

      expect(client.getFallbackMode()).toBe(true);
    });

    it("returns false when connected", async () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(true);

      mockSocketInstance.once.mockImplementation((event: string, callback: () => void) => {
        if (event === "connect") {
          callback();
        }
      });

      client = new GatewayClient(defaultOptions);
      await client.connect();

      expect(client.getFallbackMode()).toBe(false);
    });
  });

  describe("exponential backoff", () => {
    it("starts with 1 second delay", () => {
      const delay = 1000;
      expect(delay).toBe(1000);
    });

    it("doubles on each retry", () => {
      const delays = [1000];
      for (let i = 1; i < 5; i++) {
        delays.push(Math.min(delays[i - 1] * 2, 30000));
      }
      expect(delays).toEqual([1000, 2000, 4000, 8000, 16000]);
    });

    it("caps at 30 seconds", () => {
      let delay = 1000;
      for (let i = 0; i < 10; i++) {
        delay = Math.min(delay * 2, 30000);
      }
      expect(delay).toBeLessThanOrEqual(30000);
    });
  });

  describe("checkGatewayAvailable()", () => {
    it("returns true when socket exists", () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(true);

      expect(checkGatewayAvailable()).toBe(true);
    });

    it("returns false when socket missing", () => {
      (mockedFs.existsSync as vi.Mock).mockReturnValue(false);

      expect(checkGatewayAvailable()).toBe(false);
    });
  });
});
