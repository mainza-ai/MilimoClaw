"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
const vitest_1 = require("vitest");
// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------
// Mock node:fs — controls isInsideSandbox() detection
vitest_1.vi.mock("node:fs", () => ({
    existsSync: vitest_1.vi.fn(() => false),
}));
// Mock node:child_process — controls openshell command results
vitest_1.vi.mock("node:child_process", () => ({
    exec: vitest_1.vi.fn(),
}));
// Mock state loader — controls plugin state
vitest_1.vi.mock("../blueprint/state.js", () => ({
    loadState: vitest_1.vi.fn(),
}));
// Import after mocks are set up
const { existsSync } = await import("node:fs");
const { exec } = await import("node:child_process");
const { loadState } = await import("../blueprint/state.js");
const { cliStatus } = await import("./status.js");
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function blankState() {
    return {
        lastRunId: null,
        lastAction: null,
        blueprintVersion: null,
        sandboxName: null,
        migrationSnapshot: null,
        hostBackupPath: null,
        createdAt: null,
        updatedAt: new Date().toISOString(),
    };
}
function populatedState() {
    return {
        lastRunId: "run-a1b2c3d4",
        lastAction: "migrate",
        blueprintVersion: "0.1.0",
        sandboxName: "openclaw",
        migrationSnapshot: "/root/.nemoclaw/snapshots/pre-migrate.tar.gz",
        hostBackupPath: "/root/.nemoclaw/backups/host-backup",
        createdAt: "2026-03-15T10:30:00.000Z",
        updatedAt: "2026-03-15T10:32:45.000Z",
    };
}
const defaultConfig = {
    blueprintVersion: "latest",
    blueprintRegistry: "ghcr.io/nvidia/nemoclaw-blueprint",
    sandboxName: "openclaw",
    inferenceProvider: "nvidia",
};
/** Create a logger that captures all info() calls into an array. */
function captureLogger() {
    const lines = [];
    return {
        lines,
        logger: {
            info: (msg) => lines.push(msg),
            warn: (msg) => lines.push(`WARN: ${msg}`),
            error: (msg) => lines.push(`ERROR: ${msg}`),
            debug: (_msg) => { },
        },
    };
}
/**
 * Make the exec mock resolve with the given stdout, or reject if error is set.
 * Routes by command substring so sandbox and inference calls can differ.
 */
function mockExec(responses) {
    vitest_1.vi.mocked(exec).mockImplementation(((cmd, _opts, callback) => {
        // promisify(exec)(cmd, opts) calls exec(cmd, opts, callback)
        for (const [substring, response] of Object.entries(responses)) {
            if (cmd.includes(substring)) {
                if (response instanceof Error) {
                    callback?.(response, { stdout: "", stderr: response.message });
                }
                else {
                    callback?.(null, { stdout: response, stderr: "" });
                }
                return;
            }
        }
        // Default: command not found
        callback?.(new Error(`command not found: ${cmd}`), { stdout: "", stderr: "" });
    }));
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
(0, vitest_1.beforeEach)(() => {
    vitest_1.vi.resetAllMocks();
    vitest_1.vi.mocked(existsSync).mockReturnValue(false);
    vitest_1.vi.mocked(loadState).mockReturnValue(blankState());
    mockExec({});
});
(0, vitest_1.describe)("cliStatus", () => {
    // =========================================================================
    // Scenario 1: Host — no openshell, blank state
    // =========================================================================
    (0, vitest_1.describe)("host — no openshell, blank state", () => {
        (0, vitest_1.it)("shows 'not running' and 'Not configured' in text output", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Status:  not running");
            (0, vitest_1.expect)(output).toContain("Not configured");
            (0, vitest_1.expect)(output).not.toContain("inside sandbox");
            (0, vitest_1.expect)(output).not.toContain("active (inside sandbox)");
        });
        (0, vitest_1.it)("includes insideSandbox: false in JSON output", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(false);
            (0, vitest_1.expect)(data.sandbox.insideSandbox).toBe(false);
            (0, vitest_1.expect)(data.sandbox.running).toBe(false);
            (0, vitest_1.expect)(data.inference.insideSandbox).toBe(false);
            (0, vitest_1.expect)(data.inference.configured).toBe(false);
        });
        (0, vitest_1.it)("shows 'No operations have been performed yet'", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            (0, vitest_1.expect)(lines.join("\n")).toContain("No operations have been performed yet.");
        });
    });
    // =========================================================================
    // Scenario 2: Host — sandbox running, inference configured
    // =========================================================================
    (0, vitest_1.describe)("host — sandbox running, inference configured", () => {
        (0, vitest_1.beforeEach)(() => {
            mockExec({
                "sandbox status": JSON.stringify({ state: "running", uptime: "2h 14m" }),
                "inference get": JSON.stringify({
                    provider: "nvidia",
                    model: "nemotron-3-super-120b",
                    endpoint: "https://integrate.api.nvidia.com",
                }),
            });
        });
        (0, vitest_1.it)("shows running sandbox with uptime in text output", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Status:  running");
            (0, vitest_1.expect)(output).toContain("Uptime:  2h 14m");
            (0, vitest_1.expect)(output).toContain("Name:    openclaw");
            (0, vitest_1.expect)(output).not.toContain("inside sandbox");
        });
        (0, vitest_1.it)("shows configured inference in text output", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Provider:  nvidia");
            (0, vitest_1.expect)(output).toContain("Model:     nemotron-3-super-120b");
            (0, vitest_1.expect)(output).toContain("Endpoint:  https://integrate.api.nvidia.com");
        });
        (0, vitest_1.it)("returns correct JSON structure", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(false);
            (0, vitest_1.expect)(data.sandbox.running).toBe(true);
            (0, vitest_1.expect)(data.sandbox.uptime).toBe("2h 14m");
            (0, vitest_1.expect)(data.sandbox.insideSandbox).toBe(false);
            (0, vitest_1.expect)(data.inference.configured).toBe(true);
            (0, vitest_1.expect)(data.inference.provider).toBe("nvidia");
            (0, vitest_1.expect)(data.inference.insideSandbox).toBe(false);
        });
    });
    // =========================================================================
    // Scenario 3: Host — sandbox running, no inference
    // =========================================================================
    (0, vitest_1.describe)("host — sandbox running, no inference", () => {
        (0, vitest_1.beforeEach)(() => {
            mockExec({
                "sandbox status": JSON.stringify({ state: "running", uptime: "45m 12s" }),
                "inference get": new Error("no inference configured"),
            });
        });
        (0, vitest_1.it)("shows running sandbox but 'Not configured' inference", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Status:  running");
            (0, vitest_1.expect)(output).toContain("Not configured");
            (0, vitest_1.expect)(output).not.toContain("unable to query");
        });
        (0, vitest_1.it)("JSON shows sandbox running, inference not configured, not inside sandbox", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.sandbox.running).toBe(true);
            (0, vitest_1.expect)(data.inference.configured).toBe(false);
            (0, vitest_1.expect)(data.inference.insideSandbox).toBe(false);
        });
    });
    // =========================================================================
    // Scenario 4: Inside sandbox — core bug fix
    // =========================================================================
    (0, vitest_1.describe)("inside sandbox — core bug fix", () => {
        (0, vitest_1.beforeEach)(() => {
            vitest_1.vi.mocked(existsSync).mockImplementation((p) => {
                const path = String(p);
                return path === "/sandbox/.openclaw" || path === "/sandbox/.nemoclaw";
            });
        });
        (0, vitest_1.it)("shows 'active (inside sandbox)' instead of 'not running'", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("active (inside sandbox)");
            (0, vitest_1.expect)(output).not.toContain("Status:  not running");
        });
        (0, vitest_1.it)("shows sandbox context banner", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Context: running inside an active OpenShell sandbox");
            (0, vitest_1.expect)(output).toContain("Host sandbox state is not inspectable from inside the sandbox.");
        });
        (0, vitest_1.it)("shows 'unable to query' instead of 'Not configured'", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("unable to query from inside sandbox");
            (0, vitest_1.expect)(output).not.toContain("Not configured");
        });
        (0, vitest_1.it)("does not call openshell commands", async () => {
            const { logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            (0, vitest_1.expect)(exec).not.toHaveBeenCalled();
        });
        (0, vitest_1.it)("JSON output has insideSandbox: true everywhere", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(true);
            (0, vitest_1.expect)(data.sandbox.insideSandbox).toBe(true);
            (0, vitest_1.expect)(data.sandbox.running).toBe(false);
            (0, vitest_1.expect)(data.inference.insideSandbox).toBe(true);
            (0, vitest_1.expect)(data.inference.configured).toBe(false);
        });
    });
    // =========================================================================
    // Scenario 5: Inside sandbox with prior plugin state
    // =========================================================================
    (0, vitest_1.describe)("inside sandbox — with prior plugin state", () => {
        (0, vitest_1.beforeEach)(() => {
            vitest_1.vi.mocked(existsSync).mockImplementation((p) => {
                const path = String(p);
                return path === "/sandbox/.openclaw" || path === "/sandbox/.nemoclaw";
            });
            vitest_1.vi.mocked(loadState).mockReturnValue(populatedState());
        });
        (0, vitest_1.it)("shows plugin state from state file", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Last action:      migrate");
            (0, vitest_1.expect)(output).toContain("Blueprint:        0.1.0");
            (0, vitest_1.expect)(output).toContain("Run ID:           run-a1b2c3d4");
        });
        (0, vitest_1.it)("shows rollback section when migrationSnapshot exists", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Rollback:");
            (0, vitest_1.expect)(output).toContain("Snapshot:  /root/.nemoclaw/snapshots/pre-migrate.tar.gz");
            (0, vitest_1.expect)(output).toContain("openclaw nemoclaw eject");
        });
        (0, vitest_1.it)("JSON includes full nemoclaw state alongside insideSandbox: true", async () => {
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(true);
            (0, vitest_1.expect)(data.nemoclaw.lastAction).toBe("migrate");
            (0, vitest_1.expect)(data.nemoclaw.blueprintVersion).toBe("0.1.0");
            (0, vitest_1.expect)(data.nemoclaw.lastRunId).toBe("run-a1b2c3d4");
            (0, vitest_1.expect)(data.nemoclaw.migrationSnapshot).toBe("/root/.nemoclaw/snapshots/pre-migrate.tar.gz");
        });
    });
    // =========================================================================
    // Edge cases
    // =========================================================================
    (0, vitest_1.describe)("edge cases", () => {
        (0, vitest_1.it)("uses state.sandboxName when available", async () => {
            vitest_1.vi.mocked(loadState).mockReturnValue({
                ...blankState(),
                sandboxName: "custom-sandbox",
            });
            mockExec({
                "sandbox status": JSON.stringify({ state: "running", uptime: "1m" }),
                "inference get": new Error("not configured"),
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Name:    custom-sandbox");
            // Verify the exec call used the custom sandbox name
            (0, vitest_1.expect)(exec).toHaveBeenCalledWith(vitest_1.expect.stringContaining("custom-sandbox"), vitest_1.expect.anything(), vitest_1.expect.anything());
        });
        (0, vitest_1.it)("defaults sandbox name to 'openclaw' when state has none", async () => {
            mockExec({
                "sandbox status": new Error("not found"),
                "inference get": new Error("not configured"),
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            // Verify exec was called with default name
            (0, vitest_1.expect)(exec).toHaveBeenCalledWith(vitest_1.expect.stringContaining("openclaw"), vitest_1.expect.anything(), vitest_1.expect.anything());
        });
        (0, vitest_1.it)("only detects sandbox via /sandbox/.openclaw", async () => {
            vitest_1.vi.mocked(existsSync).mockImplementation((p) => {
                return String(p) === "/sandbox/.openclaw";
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(true);
        });
        (0, vitest_1.it)("only detects sandbox via /sandbox/.nemoclaw", async () => {
            vitest_1.vi.mocked(existsSync).mockImplementation((p) => {
                return String(p) === "/sandbox/.nemoclaw";
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: true, logger, pluginConfig: defaultConfig });
            const data = JSON.parse(lines.join(""));
            (0, vitest_1.expect)(data.insideSandbox).toBe(true);
        });
        (0, vitest_1.it)("handles sandbox running but with missing uptime field", async () => {
            mockExec({
                "sandbox status": JSON.stringify({ state: "running" }),
                "inference get": new Error("not configured"),
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            const output = lines.join("\n");
            (0, vitest_1.expect)(output).toContain("Status:  running");
            (0, vitest_1.expect)(output).toContain("Uptime:  unknown");
        });
        (0, vitest_1.it)("no rollback section when migrationSnapshot is null", async () => {
            vitest_1.vi.mocked(loadState).mockReturnValue({
                ...populatedState(),
                migrationSnapshot: null,
            });
            const { lines, logger } = captureLogger();
            await cliStatus({ json: false, logger, pluginConfig: defaultConfig });
            (0, vitest_1.expect)(lines.join("\n")).not.toContain("Rollback:");
        });
    });
});
//# sourceMappingURL=status.test.js.map