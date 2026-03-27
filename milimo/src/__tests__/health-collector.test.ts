// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for HealthCollector
 */

jest.mock("../lib/python-bridge", () => ({
    callPythonBridgeSafe: jest.fn(() => ({
        success: true,
        data: {
            content: {
                role: "content",
                status: "active",
                tool_count: 5,
                last_evolution: "2026-03-19T02:00:00Z",
                last_action: "2026-03-20T10:00:00Z",
                actions_this_week: 42,
                sparkline: [5, 8, 6, 7, 9, 4, 3],
            },
            ops: {
                role: "ops",
                status: "idle",
                tool_count: 3,
                last_evolution: "2026-03-12T02:00:00Z",
                last_action: "2026-03-20T08:00:00Z",
                actions_this_week: 28,
                sparkline: [3, 4, 5, 3, 4, 6, 3],
            },
            analytics: {
                role: "analytics",
                status: "processing",
                tool_count: 2,
                last_evolution: "2026-03-19T02:00:00Z",
                last_action: "2026-03-20T09:30:00Z",
                actions_this_week: 15,
                sparkline: [2, 2, 3, 2, 2, 3, 1],
            },
            finance: {
                role: "finance",
                status: "idle",
                tool_count: 4,
                last_evolution: "2026-03-05T02:00:00Z",
                last_action: "2026-03-19T16:00:00Z",
                actions_this_week: 12,
                sparkline: [1, 2, 2, 3, 2, 1, 1],
            },
            build: {
                role: "build",
                status: "idle",
                tool_count: 6,
                last_evolution: "2026-03-19T02:00:00Z",
                last_action: "2026-03-20T07:00:00Z",
                actions_this_week: 35,
                sparkline: [4, 5, 6, 5, 7, 5, 3],
            },
        },
    })),
}));

const mockedBridge = jest.requireMock("../lib/python-bridge");

import { HealthCollector } from "../warroom/health-collector";

describe("HealthCollector", () => {
    const defaultOptions = {
        squadId: "test-squad",
        blueprintDir: "/tmp/test",
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    afterEach(() => {
    });

    describe("constructor", () => {
        it("initializes with squad ID and blueprint dir", () => {
            const collector = new HealthCollector(defaultOptions);

            expect(collector.isRunning()).toBe(false);
        });

        it("uses default poll interval of 3000ms", () => {
            const collector = new HealthCollector(defaultOptions);

            expect((collector as unknown as { pollInterval: number }).pollInterval).toBe(3000);
        });

        it("accepts custom poll interval", () => {
            const collector = new HealthCollector({
                ...defaultOptions,
                pollInterval: 5000,
            });

            expect((collector as unknown as { pollInterval: number }).pollInterval).toBe(5000);
        });
    });

    describe("collectAll()", () => {
        it("calls bridge with collect_health command", async () => {
            const collector = new HealthCollector(defaultOptions);

            await collector.collectAll();

            expect(mockedBridge.callPythonBridgeSafe).toHaveBeenCalledWith(
                "collect_health",
                { squad_id: "test-squad" },
                { blueprintDir: "/tmp/test" },
            );
        });

        it("returns ClawHealthMap keyed by role", async () => {
            const collector = new HealthCollector(defaultOptions);

            const health = await collector.collectAll();

            expect(health.content).toBeDefined();
            expect(health.ops).toBeDefined();
            expect(health.analytics).toBeDefined();
            expect(health.finance).toBeDefined();
            expect(health.build).toBeDefined();
        });

        it("includes all required health fields", async () => {
            const collector = new HealthCollector(defaultOptions);

            const health = await collector.collectAll();

            expect(health.content.role).toBe("content");
            expect(health.content.status).toBeDefined();
            expect(health.content.tool_count).toBeGreaterThanOrEqual(0);
            expect(health.content.last_evolution).toBeDefined();
            expect(health.content.last_action).toBeDefined();
            expect(health.content.actions_this_week).toBeGreaterThanOrEqual(0);
            expect(Array.isArray(health.content.sparkline)).toBe(true);
        });
    });

    describe("startPolling()", () => {
        it("starts polling at configured interval", () => {
            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();

            collector.startPolling(onUpdate);

            expect(collector.isRunning()).toBe(true);

            collector.stopPolling();
        });

        it("calls onUpdate immediately on start", async () => {
            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();

            collector.startPolling(onUpdate);

            await Promise.resolve();

            expect(onUpdate).toHaveBeenCalled();

            collector.stopPolling();
        });

        it("returns cleanup function that stops polling", () => {
            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();

            const cleanup = collector.startPolling(onUpdate);
            cleanup();

            expect(collector.isRunning()).toBe(false);
        });

        it("calls onError on bridge failure", async () => {
            mockedBridge.callPythonBridgeSafe.mockReturnValueOnce({
                success: false,
                error: "Bridge error",
            });

            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();
            const onError = jest.fn();

            collector.startPolling(onUpdate, onError);

            await new Promise((resolve) => setTimeout(resolve, 10));

            expect(onError).toHaveBeenCalled();

            collector.stopPolling();
        });

        it("does NOT stop polling on error", async () => {
            mockedBridge.callPythonBridgeSafe
                .mockReturnValueOnce({ success: false, error: "Error 1" })
                .mockReturnValueOnce({ success: true, data: {} });

            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();
            const onError = jest.fn();

            collector.startPolling(onUpdate, onError);

            await Promise.resolve();

            expect(collector.isRunning()).toBe(true);

            collector.stopPolling();
        });
    });

    describe("stopPolling()", () => {
        it("sets running to false", () => {
            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();

            collector.startPolling(onUpdate);
            collector.stopPolling();

            expect(collector.isRunning()).toBe(false);
        });

        it("clears the interval", () => {
            const collector = new HealthCollector(defaultOptions);
            const onUpdate = jest.fn();

            collector.startPolling(onUpdate);
            collector.stopPolling();

            expect((collector as unknown as { intervalId: NodeJS.Timeout | null }).intervalId).toBeNull();
        });
    });

    describe("deriveStatus()", () => {
        it("returns active if last_action within 60 seconds", () => {
            const collector = new HealthCollector(defaultOptions);

            const now = new Date();
            const fiftySecondsAgo = new Date(now.getTime() - 50000).toISOString();

            const health = {
                role: "content",
                status: "idle" as const,
                tool_count: 5,
                last_evolution: null,
                last_action: fiftySecondsAgo,
                actions_this_week: 10,
                sparkline: [1, 2, 3, 4, 5, 6, 7],
            };

            expect(collector.deriveStatus(health)).toBe("active");
        });

        it("returns idle if last_action over 60 seconds ago", () => {
            const collector = new HealthCollector(defaultOptions);

            const now = new Date();
            const twoMinutesAgo = new Date(now.getTime() - 120000).toISOString();

            const health = {
                role: "content",
                status: "idle" as const,
                tool_count: 5,
                last_evolution: null,
                last_action: twoMinutesAgo,
                actions_this_week: 10,
                sparkline: [1, 2, 3, 4, 5, 6, 7],
            };

            expect(collector.deriveStatus(health)).toBe("idle");
        });

        it("returns processing if status is processing", () => {
            const collector = new HealthCollector(defaultOptions);

            const health = {
                role: "content",
                status: "processing" as const,
                tool_count: 5,
                last_evolution: null,
                last_action: null,
                actions_this_week: 10,
                sparkline: [1, 2, 3, 4, 5, 6, 7],
            };

            expect(collector.deriveStatus(health)).toBe("processing");
        });

        it("returns error if status is error", () => {
            const collector = new HealthCollector(defaultOptions);

            const health = {
                role: "content",
                status: "error" as const,
                tool_count: 0,
                last_evolution: null,
                last_action: null,
                actions_this_week: 0,
                sparkline: [0, 0, 0, 0, 0, 0, 0],
            };

            expect(collector.deriveStatus(health)).toBe("error");
        });

        it("returns idle if last_action is null", () => {
            const collector = new HealthCollector(defaultOptions);

            const health = {
                role: "content",
                status: "idle" as const,
                tool_count: 5,
                last_evolution: null,
                last_action: null,
                actions_this_week: 10,
                sparkline: [1, 2, 3, 4, 5, 6, 7],
            };

            expect(collector.deriveStatus(health)).toBe("idle");
        });

        it("handles invalid last_action date", () => {
            const collector = new HealthCollector(defaultOptions);

            const health = {
                role: "content",
                status: "idle" as const,
                tool_count: 5,
                last_evolution: null,
                last_action: "invalid-date",
                actions_this_week: 10,
                sparkline: [1, 2, 3, 4, 5, 6, 7],
            };

            expect(collector.deriveStatus(health)).toBe("idle");
        });
    });

    describe("sparkline format", () => {
        it("returns 7 integers for sparkline", async () => {
            const collector = new HealthCollector(defaultOptions);

            const health = await collector.collectAll();

            expect(health.content.sparkline).toHaveLength(7);
            for (const val of health.content.sparkline) {
                expect(typeof val).toBe("number");
            }
        });
    });

    describe("error resilience", () => {
        it("throws on bridge failure", async () => {
            mockedBridge.callPythonBridgeSafe.mockReturnValueOnce({
                success: false,
                error: "Connection refused",
            });

            const collector = new HealthCollector(defaultOptions);

            await expect(collector.collectAll()).rejects.toThrow("Connection refused");
        });
    });
});
