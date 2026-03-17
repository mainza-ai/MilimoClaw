// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Unit tests for the Milimo Claw CLI plugin.
 *
 * Tests verify that:
 * - The plugin module exports the expected shape
 * - CLI commands accept --help without errors
 * - Config parsing handles defaults and overrides
 * - State management reads/writes correctly
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const fs = require("fs");
const os = require("os");

// ---------------------------------------------------------------------------
// Plugin exports
// ---------------------------------------------------------------------------

describe("Milimo plugin exports", () => {
  it("default export is a function (register)", () => {
    const plugin = require("../milimo/dist/index.js");
    assert.equal(typeof plugin.default, "function");
  });

  it("exports getPluginConfig", () => {
    const plugin = require("../milimo/dist/index.js");
    assert.equal(typeof plugin.getPluginConfig, "function");
  });

  it("exports CLAW_ROLES with 5 roles", () => {
    const plugin = require("../milimo/dist/index.js");
    assert.equal(plugin.CLAW_ROLES.length, 5);
    assert.deepEqual(plugin.CLAW_ROLES, ["content", "ops", "analytics", "finance", "build"]);
  });
});

// ---------------------------------------------------------------------------
// Config parsing
// ---------------------------------------------------------------------------

describe("Milimo config parsing", () => {
  it("returns defaults when pluginConfig is empty", () => {
    const { getPluginConfig } = require("../milimo/dist/index.js");
    const api = { pluginConfig: {} };
    const config = getPluginConfig(api);

    assert.equal(config.squadName, "");
    assert.equal(config.clawRole, "");
    assert.equal(config.meshSecret, "");
    assert.equal(config.blueprintDir, "/opt/milimo-blueprint");
  });

  it("reads valid config values", () => {
    const { getPluginConfig } = require("../milimo/dist/index.js");
    const api = {
      pluginConfig: {
        squadName: "test-squad",
        clawRole: "content",
        meshSecret: "s3cret",
        blueprintDir: "/custom/path",
      },
    };
    const config = getPluginConfig(api);

    assert.equal(config.squadName, "test-squad");
    assert.equal(config.clawRole, "content");
    assert.equal(config.meshSecret, "s3cret");
    assert.equal(config.blueprintDir, "/custom/path");
  });

  it("rejects invalid claw role", () => {
    const { getPluginConfig } = require("../milimo/dist/index.js");
    const api = { pluginConfig: { clawRole: "invalid-role" } };
    const config = getPluginConfig(api);

    // Should fall back to default (empty string)
    assert.equal(config.clawRole, "");
  });

  it("accepts all valid claw roles", () => {
    const { getPluginConfig, CLAW_ROLES } = require("../milimo/dist/index.js");

    for (const role of CLAW_ROLES) {
      const api = { pluginConfig: { clawRole: role } };
      const config = getPluginConfig(api);
      assert.equal(config.clawRole, role, `Role ${role} should be accepted`);
    }
  });
});

// ---------------------------------------------------------------------------
// State management
// ---------------------------------------------------------------------------

describe("Milimo state management", () => {
  let tmpHome;

  beforeEach(() => {
    tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "milimo-test-"));
    process.env.HOME = tmpHome;
  });

  afterEach(() => {
    fs.rmSync(tmpHome, { recursive: true, force: true });
  });

  it("loadMilimoState returns null when no state exists", () => {
    const { loadMilimoState } = require("../milimo/dist/commands/init.js");
    assert.equal(loadMilimoState(), null);
  });

  it("loadMilimoState reads saved state", () => {
    const { loadMilimoState } = require("../milimo/dist/commands/init.js");

    // Manually write state
    const stateDir = path.join(tmpHome, ".milimo");
    fs.mkdirSync(stateDir, { recursive: true });
    const state = {
      squadName: "test-squad",
      clawRole: "content",
      template: "content-agency",
      solo: false,
      meshMembers: ["content"],
      initializedAt: "2026-03-17T00:00:00Z",
      blueprintVersion: "0.1.0",
    };
    fs.writeFileSync(path.join(stateDir, "state.json"), JSON.stringify(state));

    const loaded = loadMilimoState();
    assert.deepEqual(loaded, state);
  });

  it("loadMilimoState returns null on corrupted file", () => {
    const { loadMilimoState } = require("../milimo/dist/commands/init.js");

    const stateDir = path.join(tmpHome, ".milimo");
    fs.mkdirSync(stateDir, { recursive: true });
    fs.writeFileSync(path.join(stateDir, "state.json"), "not json!");

    assert.equal(loadMilimoState(), null);
  });
});

// ---------------------------------------------------------------------------
// Slash command handler
// ---------------------------------------------------------------------------

describe("Milimo slash command", () => {
  it("handleSlashCommand returns help for empty args", () => {
    const { handleSlashCommand } = require("../milimo/dist/commands/slash.js");
    const ctx = { args: "", commandBody: "/milimo", channel: "test", isAuthorizedSender: true, config: {} };
    const api = { pluginConfig: {}, logger: { info() {}, warn() {}, error() {}, debug() {} } };

    const result = handleSlashCommand(ctx, api);
    assert.ok(result.text);
    assert.ok(result.text.includes("Milimo Claw"), "should include Milimo Claw");
    assert.ok(result.text.includes("status"), "should mention status subcommand");
  });

  it("handleSlashCommand returns status for 'status' arg", () => {
    const { handleSlashCommand } = require("../milimo/dist/commands/slash.js");
    const ctx = { args: "status", commandBody: "/milimo status", channel: "test", isAuthorizedSender: true, config: {} };
    const api = { pluginConfig: {}, logger: { info() {}, warn() {}, error() {}, debug() {} } };

    const result = handleSlashCommand(ctx, api);
    assert.ok(result.text);
    // No state → should suggest init
    assert.ok(result.text.includes("init") || result.text.includes("Status"), "should suggest init or show status");
  });
});
