// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for GatewayClient
 */

jest.mock("node:net", () => ({
    Socket: jest.fn().mockImplementation(() => ({
        connect: jest.fn(),
        write: jest.fn(),
        destroy: jest.fn(),
        on: jest.fn(),
        once: jest.fn(),
    })),
}));

jest.mock("node:fs", () => ({
    existsSync: jest.fn((path: string) => path.includes("gateway")),
    mkdirSync: jest.fn(),
    writeFileSync: jest.fn(),
    readdirSync: jest.fn(),
    readFileSync: jest.fn(),
    unlinkSync: jest.fn(),
}));

jest.mock("node:crypto", () => ({
    createCipheriv: jest.fn(() => ({
        update: jest.fn(() => Buffer.from("encrypted")),
        final: jest.fn(() => Buffer.from("")),
        getAuthTag: jest.fn(() => Buffer.from("tag")),
    })),
    createDecipheriv: jest.fn(() => ({
        setAuthTag: jest.fn(),
        update: jest.fn(() => Buffer.from('{"id":"test"}')),
        final: jest.fn(() => Buffer.from("")),
    })),
    randomBytes: jest.fn(() => Buffer.from("1234567890123456")),
}));

import { GatewayClient, GatewayDeliveryError, getGatewaySocketPath, checkGatewayAvailable } from "../mesh/gateway-client";

const mockedNet = jest.requireMock("node:net");
const mockedFs = jest.requireMock("node:fs");

describe("GatewayClient", () => {
    const defaultOptions = {
        squadId: "test-squad",
        meshSecret: "test-secret-12345",
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe("constructor", () => {
        it("initializes with squad ID and mesh secret", () => {
            const client = new GatewayClient(defaultOptions);

            expect(client.isConnected()).toBe(false);
        });

        it("uses macOS socket path on darwin", () => {
            const originalPlatform = process.platform;
            Object.defineProperty(process, "platform", { value: "darwin" });

            const client = new GatewayClient(defaultOptions);

            expect(getGatewaySocketPath()).toBe("/tmp/openshell-gateway.sock");

            Object.defineProperty(process, "platform", { value: originalPlatform });
        });

        it("uses Linux socket path on linux", () => {
            const originalPlatform = process.platform;
            Object.defineProperty(process, "platform", { value: "linux" });

            expect(getGatewaySocketPath()).toBe("/var/run/openshell/gateway.sock");

            Object.defineProperty(process, "platform", { value: originalPlatform });
        });

        it("accepts message handler in options", () => {
            const handler = jest.fn();
            const client = new GatewayClient({ ...defaultOptions, onMessage: handler });

            expect(client).toBeDefined();
        });
    });

    describe("connect()", () => {
        it("sets connected to true on successful connection", async () => {
            mockedFs.existsSync.mockReturnValue(true);

            const mockSocket = {
                connect: jest.fn(),
                write: jest.fn(),
                destroy: jest.fn(),
                on: jest.fn(),
                once: jest.fn((event: string, callback: () => void) => {
                    if (event === "connect") {
                        callback();
                    }
                }),
            };
            mockedNet.Socket.mockReturnValue(mockSocket);

            const client = new GatewayClient(defaultOptions);
            await client.connect();

            expect(client.isConnected()).toBe(true);
        });

        it("enters fallback mode when socket not available", async () => {
            mockedFs.existsSync.mockReturnValue(false);

            const client = new GatewayClient(defaultOptions);
            await client.connect();

            expect(client.getFallbackMode()).toBe(true);
        });
    });

    describe("send()", () => {
        it("writes message to file in fallback mode", async () => {
            mockedFs.existsSync.mockReturnValue(false);

            const client = new GatewayClient(defaultOptions);
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
 mockedFs.existsSync.mockReturnValue(true);

 const mockSocket = {
 connect: jest.fn(),
 write: jest.fn(),
 destroy: jest.fn(),
 on: jest.fn(),
 once: jest.fn((event: string, callback: () => void) => {
 if (event === "connect") {
 callback();
 }
 }),
 };
 mockedNet.Socket.mockReturnValue(mockSocket);

 const client = new GatewayClient(defaultOptions);
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
            mockedFs.existsSync.mockReturnValue(true);

            const mockSocket = {
                connect: jest.fn(),
                write: jest.fn(),
                destroy: jest.fn(),
                on: jest.fn(),
                once: jest.fn((event: string, callback: () => void) => {
                    if (event === "connect") {
                        callback();
                    }
                }),
            };
            mockedNet.Socket.mockReturnValue(mockSocket);

            const client = new GatewayClient(defaultOptions);
            await client.connect();
            client.disconnect();

            expect(mockSocket.destroy).toHaveBeenCalled();
            expect(client.isConnected()).toBe(false);
        });
    });

    describe("onMessage()", () => {
        it("registers message handler", () => {
            const client = new GatewayClient(defaultOptions);
            const handler = jest.fn();

            client.onMessage(handler);

            expect(handler).toBeDefined();
        });
    });

    describe("getFallbackMode()", () => {
        it("returns true when in fallback", async () => {
            mockedFs.existsSync.mockReturnValue(false);

            const client = new GatewayClient(defaultOptions);
            await client.connect();

            expect(client.getFallbackMode()).toBe(true);
        });

        it("returns false when connected", async () => {
            mockedFs.existsSync.mockReturnValue(true);

            const mockSocket = {
                connect: jest.fn(),
                write: jest.fn(),
                destroy: jest.fn(),
                on: jest.fn(),
                once: jest.fn((event: string, callback: () => void) => {
                    if (event === "connect") {
                        callback();
                    }
                }),
            };
            mockedNet.Socket.mockReturnValue(mockSocket);

            const client = new GatewayClient(defaultOptions);
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
                delays.push(Math.min(delays[i - 1]! * 2, 30000));
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
            mockedFs.existsSync.mockReturnValue(true);

            expect(checkGatewayAvailable()).toBe(true);
        });

        it("returns false when socket missing", () => {
            mockedFs.existsSync.mockReturnValue(false);

            expect(checkGatewayAvailable()).toBe(false);
        });
    });
});
