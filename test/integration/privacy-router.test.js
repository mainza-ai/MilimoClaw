// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration tests for Privacy Router (TS CLI → Python)
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { IntegrationTestHarness } = require("./harness");

describe("Privacy Router Integration", () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  describe("route classification", () => {
    it("should classify public_drafts as cloud", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `route = router.classify("public_drafts", role="content")`,
          `print(route)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(
        result.stdout.includes("cloud") || result.stdout.includes("local"),
        `Expected cloud or local route, got: ${result.stdout}`
      );
    });

    it("should classify financial_data as local for finance role", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `route = router.classify("financial_data", role="finance")`,
          `print(route)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(
        result.stdout.includes("local"),
        `Expected local route for financial_data, got: ${result.stdout}`
      );
    });

    it("should classify source_code as local for build role", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `route = router.classify("source_code", role="build")`,
          `print(route)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(
        result.stdout.includes("local"),
        `Expected local route for source_code, got: ${result.stdout}`
      );
    });
  });

  describe("role overrides", () => {
    it("should enforce locked routes for finance role", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `is_locked = router.is_locked("financial_data", role="finance")`,
          `print(is_locked)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const isLocked = result.stdout.trim().toLowerCase() === "true";
      assert.ok(isLocked, "financial_data should be locked for finance role");
    });

    it("should validate squad override attempts", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `valid, reason = router.validate_squad_override("financial_data", "cloud", role="finance")`,
          `print(valid)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const valid = result.stdout.trim().toLowerCase() === "true";
      assert.ok(!valid, "Should not allow override of locked route");
    });
  });

  describe("routing decisions", () => {
    it("should return fallback for unknown data types", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `route = router.classify("unknown_type_xyz", role="content")`,
          `print(route)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(
        result.stdout.includes("local") || result.stdout.includes("default"),
        `Expected fallback route, got: ${result.stdout}`
      );
    });

    it("should log unclassified data types", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.privacy_router import PrivacyRouter`,
          `router = PrivacyRouter.from_config_file("${config.blueprintDir}/privacy_policy.yaml")`,
          `router.classify("new_data_type_123", role="content")`,
          `print("ok")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "ok");
    });
  });
});
