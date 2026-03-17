// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Milimo Claw — Evolution Engine Tests (JavaScript side)
 *
 * Tests for:
 *  - Evolution config YAML loading and structure
 *  - Evolution signals in role blueprints
 *  - War Room evolution commands (tools, evolution)
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const yaml = require("yaml");

const BLUEPRINT_DIR = path.join(__dirname, "..", "milimo-blueprint");

// ═══════════════════════════════════════════════════════════════════════
//  Evolution Config Tests
// ═══════════════════════════════════════════════════════════════════════

describe("Evolution Config", () => {
  const configPath = path.join(BLUEPRINT_DIR, "evolution_config.yaml");
  let config;

  it("evolution_config.yaml exists", () => {
    assert.ok(fs.existsSync(configPath), "evolution_config.yaml not found");
  });

  it("loads and parses correctly", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config, "Failed to parse evolution_config.yaml");
  });

  it("has schedule section", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.schedule, "Missing schedule section");
    assert.strictEqual(config.schedule.cycle_interval_days, 7);
    assert.ok(config.schedule.cycle_day, "Missing cycle_day");
    assert.ok(typeof config.schedule.allow_manual_trigger === "boolean");
  });

  it("has observation section", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.observation, "Missing observation section");
    assert.strictEqual(config.observation.window_days, 7);
    assert.ok(config.observation.minimum_actions > 0);
    assert.ok(config.observation.cross_signal_lookback_days > 0);
  });

  it("has detection section with valid pattern types", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.detection, "Missing detection section");
    assert.ok(config.detection.minimum_confidence > 0);
    assert.ok(Array.isArray(config.detection.pattern_types));

    const validTypes = [
      "classifier",
      "optimizer",
      "predictor",
      "generator_variant",
      "anomaly_detector",
    ];
    for (const pt of config.detection.pattern_types) {
      assert.ok(validTypes.includes(pt), `Invalid pattern type: ${pt}`);
    }
  });

  it("has building section", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.building, "Missing building section");
    assert.ok(config.building.backtest_window_weeks > 0);
    assert.ok(config.building.minimum_improvement_percent > 0);
    assert.strictEqual(config.building.inference_backend, "local-nim");
  });

  it("has deployment section", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.deployment, "Missing deployment section");
    assert.ok(config.deployment.max_tools_per_claw > 0);
    assert.ok(typeof config.deployment.require_proposal_approval === "boolean");
    assert.ok(typeof config.deployment.auto_disable_on_regression === "boolean");
  });

  it("has logging section", () => {
    const raw = fs.readFileSync(configPath, "utf8");
    config = yaml.parse(raw);
    assert.ok(config.logging, "Missing logging section");
    assert.ok(typeof config.logging.notify_war_room === "boolean");
  });
});

// ═══════════════════════════════════════════════════════════════════════
//  Evolution Signals in Role Blueprints
// ═══════════════════════════════════════════════════════════════════════

describe("Evolution Signals in Blueprints", () => {
  const ROLES = ["content", "ops", "analytics", "finance", "build"];

  for (const role of ROLES) {
    describe(`${role} claw`, () => {
      const rolePath = path.join(
        BLUEPRINT_DIR,
        "roles",
        `${role}-claw.yaml`
      );
      let blueprint;

      it(`${role}-claw.yaml exists`, () => {
        assert.ok(
          fs.existsSync(rolePath),
          `${role}-claw.yaml not found`
        );
      });

      it("has evolution_signals section", () => {
        const raw = fs.readFileSync(rolePath, "utf8");
        blueprint = yaml.parse(raw);
        assert.ok(
          blueprint.evolution_signals,
          `${role}-claw.yaml missing evolution_signals`
        );
      });

      it("evolution_signals has primary signal", () => {
        const raw = fs.readFileSync(rolePath, "utf8");
        blueprint = yaml.parse(raw);
        assert.ok(
          blueprint.evolution_signals.primary,
          `${role}-claw.yaml missing evolution_signals.primary`
        );
        assert.ok(
          typeof blueprint.evolution_signals.primary === "string",
          "primary should be a string"
        );
      });

      it("evolution_signals has initial_tools array", () => {
        const raw = fs.readFileSync(rolePath, "utf8");
        blueprint = yaml.parse(raw);
        const tools = blueprint.evolution_signals.initial_tools;
        assert.ok(
          Array.isArray(tools),
          `${role}-claw.yaml evolution_signals.initial_tools should be an array`
        );
        assert.ok(tools.length >= 1, "Should have at least 1 initial tool");
      });

      it("each initial_tool has name, target_week, and description", () => {
        const raw = fs.readFileSync(rolePath, "utf8");
        blueprint = yaml.parse(raw);
        for (const tool of blueprint.evolution_signals.initial_tools) {
          assert.ok(tool.name, "initial_tool missing name");
          assert.ok(
            typeof tool.target_week === "number",
            "initial_tool target_week should be a number"
          );
          assert.ok(tool.description, "initial_tool missing description");
        }
      });
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════
//  Orchestrator Module Existence
// ═══════════════════════════════════════════════════════════════════════

describe("Evolution Engine Modules", () => {
  const MODULES = [
    "operation_log.py",
    "pattern_detector.py",
    "tool_proposal.py",
    "tool_builder.py",
    "tool_registry.py",
    "evolution_cycle.py",
    "blueprint_manager.py",
  ];

  for (const mod of MODULES) {
    it(`${mod} exists in orchestrator/`, () => {
      const modPath = path.join(BLUEPRINT_DIR, "orchestrator", mod);
      assert.ok(fs.existsSync(modPath), `${mod} not found`);
    });

    it(`${mod} is not empty`, () => {
      const modPath = path.join(BLUEPRINT_DIR, "orchestrator", mod);
      const stat = fs.statSync(modPath);
      assert.ok(stat.size > 500, `${mod} is too small (${stat.size} bytes)`);
    });
  }
});
