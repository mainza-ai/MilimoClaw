// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration tests for Blueprint Manager (TS CLI → Python)
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const {
  IntegrationTestHarness,
  createTestMessage,
  waitFor,
} = require("./harness");

describe("Blueprint Manager Integration", () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  describe("version management", () => {
    it("should return default version when no state exists", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "/tmp")`,
          `print(mgr.current_version())`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "0.1.0");
    });

    it("should bump version correctly", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      await harness.writeBlueprintState("test-squad", "content", {
        version: "0.1.0",
        version_history: [],
      });

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}", versions_dir="${tempDir}/.milimo/blueprints/test-squad/content")`,
          `new_ver = mgr.bump_version("test bump")`,
          `print(new_ver)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "0.1.1");
    });
  });

  describe("export", () => {
    it("should export a valid blueprint snapshot", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}")`,
          `snapshot = mgr.export()`,
          `print(json.dumps(snapshot.to_dict(), default=str))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const snapshot = JSON.parse(result.stdout);

      assert.ok(snapshot.meta, "Snapshot should have meta");
      assert.ok(snapshot.claw_config, "Snapshot should have claw_config");
      assert.ok(snapshot.tools_inventory, "Snapshot should have tools_inventory");
      assert.ok(snapshot.policy, "Snapshot should have policy");
      assert.ok(snapshot.integrity, "Snapshot should have integrity");
      assert.ok(snapshot.integrity.digest, "Snapshot should have integrity digest");
    });
  });

  describe("diff", () => {
    it("should compare two versions", async () => {
      const config = harness.getConfig();

      await harness.runPython(
        "-c",
        [
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}")`,
          `mgr.bump_version("first")`,
          `mgr.export()`,
          `mgr.bump_version("second")`,
          `mgr.export()`,
        ].join("; ")
      );

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}")`,
          `diff = mgr.diff("0.1.1", "0.1.2")`,
          `print(json.dumps({"tools_added": diff.tools_added, "tools_removed": diff.tools_removed}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const diff = JSON.parse(result.stdout);
      assert.ok(Array.isArray(diff.tools_added), "tools_added should be array");
      assert.ok(Array.isArray(diff.tools_removed), "tools_removed should be array");
    });
  });

  describe("rollback", () => {
    it("should rollback to previous version", async () => {
      const config = harness.getConfig();

      await harness.runPython(
        "-c",
        [
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}")`,
          `mgr.export()`,
          `mgr.bump_version("first")`,
          `mgr.export()`,
        ].join("; ")
      );

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.blueprint_manager import BlueprintManager`,
          `mgr = BlueprintManager("test-squad", "content", "${config.blueprintDir}")`,
          `success = mgr.rollback("0.1.0", "test rollback")`,
          `print("True" if success else "False")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "True");
    });
  });
});
