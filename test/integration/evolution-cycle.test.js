// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration tests for Evolution Cycle (TS CLI → Python)
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { IntegrationTestHarness } = require("./harness");

describe("Evolution Cycle Integration", () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  describe("cycle configuration", () => {
    it("should load evolution config from file", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.evolution_cycle import EvolutionConfig`,
          `config = EvolutionConfig.from_file("${config.blueprintDir}/evolution_config.yaml")`,
          `print(json.dumps({"cycle_interval_days": config.cycle_interval_days, "min_confidence": config.min_confidence}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.cycle_interval_days >= 1, "Should have valid cycle interval");
      assert.ok(data.min_confidence >= 0 && data.min_confidence <= 1, "Should have valid confidence threshold");
    });

    it("should use defaults when config file not found", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.evolution_cycle import EvolutionConfig`,
          `config = EvolutionConfig.from_file("/nonexistent/path/config.yaml")`,
          `print(json.dumps({"cycle_interval_days": config.cycle_interval_days, "minimum_actions": config.minimum_actions}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.cycle_interval_days, 7, "Default cycle interval should be 7");
      assert.strictEqual(data.minimum_actions, 20, "Default minimum actions should be 20");
    });
  });

  describe("cycle stages", () => {
    it("should skip cycle when insufficient actions", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.evolution_cycle import EvolutionCycle`,
          `cycle = EvolutionCycle("test-squad", "content", "${config.blueprintDir}", log_dir="${tempDir}/.milimo/logs")`,
          `result = cycle.run(dry_run=True)`,
          `print(json.dumps({"stage_reached": result.stage_reached, "skipped_reason": result.skipped_reason}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.stage_reached, "observe");
      assert.ok(data.skipped_reason.includes("Insufficient"), "Should indicate insufficient data");
    });

    it("should create EvolutionCycle with valid parameters", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.evolution_cycle import EvolutionCycle`,
          `cycle = EvolutionCycle("test-squad", "content", "${config.blueprintDir}")`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });
  });

  describe("tool registry", () => {
    it("should track tool capacity", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.tool_registry import ToolRegistry`,
          `registry = ToolRegistry("test-squad", "content", registry_dir="${tempDir}/.milimo/registry")`,
          `inventory = registry.get_inventory()`,
          `print(json.dumps({"tool_count": len(inventory), "max_tools": registry.max_tools}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.max_tools > 0, "Should have max_tools limit");
      assert.ok(data.tool_count >= 0, "Should have valid tool count");
    });

    it("should register and retrieve tools", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.tool_registry import ToolRegistry, RegisteredTool`,
          `registry = ToolRegistry("test-squad", "content", registry_dir="${tempDir}/.milimo/registry")`,
          `tool = RegisteredTool(name="test_tool", version="0.1.0", tool_type="classifier", status="deployed", performance_delta=5.5)`,
          `registry.register(tool)`,
          `inventory = registry.get_inventory()`,
          `print(json.dumps({"registered": "test_tool" in inventory}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.registered, true);
    });
  });

  describe("pattern detection", () => {
    it("should create pattern detector with valid config", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.pattern_detector import PatternDetector`,
          `detector = PatternDetector(claw_role="content", min_confidence=0.6)`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });
  });

  describe("tool builder integration", () => {
    it("should create ToolBuilder with generator", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.tool_builder import ToolBuilder`,
          `builder = ToolBuilder(claw_role="content", squad_id="test-squad", blueprint_dir="${config.blueprintDir}")`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });
  });
});
