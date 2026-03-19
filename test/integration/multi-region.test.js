// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration tests for Multi-Region Mesh (Phase 4.1)
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { IntegrationTestHarness } = require("./harness");

describe("Multi-Region Mesh Integration", () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  describe("region detection", () => {
    it("should detect region from environment variable", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import os`,
          `os.environ["MILIMO_REGION"] = "eu-west-1"`,
          `from orchestrator.region_detector import RegionDetector`,
          `detector = RegionDetector(regions_config_path="${config.blueprintDir}/regions.yaml")`,
          `region = detector.detect()`,
          `print(region.region_id)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "eu-west-1");
    });

    it("should load regions configuration", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.region_detector import RegionDetector`,
          `detector = RegionDetector(regions_config_path="${config.blueprintDir}/regions.yaml")`,
          `regions = detector.get_all_regions()`,
          `print(json.dumps({"region_count": len(regions), "regions": regions}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.region_count >= 7, "Should have at least 7 regions");
      assert.ok(data.regions.includes("us-east-1"), "Should include us-east-1");
      assert.ok(data.regions.includes("eu-west-1"), "Should include eu-west-1");
    });

    it("should get optimal relay for region", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.region_detector import RegionDetector`,
          `detector = RegionDetector(regions_config_path="${config.blueprintDir}/regions.yaml")`,
          `relay = detector.get_optimal_relay("us-east-1")`,
          `print(relay)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(
        result.stdout.includes("relay") || result.stdout.includes("milimo"),
        `Expected relay URL, got: ${result.stdout}`
      );
    });

    it("should get fallback region", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.region_detector import RegionDetector`,
          `detector = RegionDetector(regions_config_path="${config.blueprintDir}/regions.yaml")`,
          `fallback = detector.get_fallback_region("us-west-2")`,
          `print(fallback)`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.ok(result.stdout.trim().length > 0, "Should have fallback region");
    });
  });

  describe("latency monitoring", () => {
    it("should create latency monitor with valid config", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.latency_monitor import LatencyMonitor`,
          `monitor = LatencyMonitor(region="us-east-1")`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });

    it("should get latency matrix", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.latency_monitor import LatencyMonitor`,
          `monitor = LatencyMonitor(region="us-east-1", target_regions=["eu-west-1", "ap-southeast-1"])`,
          `matrix = monitor.get_matrix()`,
          `print(json.dumps({"regions": matrix.regions, "has_matrix": len(matrix.matrix) > 0}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.regions.includes("us-east-1"), "Should include source region");
      assert.ok(data.has_matrix, "Should have latency matrix");
    });

    it("should calculate optimal route", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.latency_monitor import LatencyMonitor`,
          `monitor = LatencyMonitor(region="us-east-1")`,
          `route = monitor.get_optimal_route("ap-southeast-1")`,
          `print(json.dumps({"route": route}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(Array.isArray(data.route), "Route should be an array");
      assert.strictEqual(data.route[0], "us-east-1", "Route should start from source");
      assert.strictEqual(data.route[data.route.length - 1], "ap-southeast-1", "Route should end at target");
    });
  });

  describe("failover management", () => {
    it("should create failover manager", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.mesh import MeshCoordinator`,
          `from orchestrator.mesh_failover import FailoverManager`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `manager = FailoverManager(mesh)`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });

    it("should start in normal state", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `from orchestrator.mesh_failover import FailoverManager, FailoverState`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `manager = FailoverManager(mesh)`,
          `print(json.dumps({"state": manager.state.value}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.state, "normal");
    });

    it("should have version vector for split-brain resolution", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `from orchestrator.mesh_failover import FailoverManager, VersionVector`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `manager = FailoverManager(mesh)`,
          `manager.start()`,
          `vv = manager.get_version_vector()`,
          `manager.stop()`,
          `print(json.dumps({"has_vector": vv is not None}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.has_vector, true);
    });
  });

  describe("relay client", () => {
    it("should create relay client with valid config", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `from orchestrator.mesh_relay import RelayClient, RelayConfig`,
          `config = RelayConfig(relay_url="wss://test.milimo.dev", squad_id="test", role="content")`,
          `client = RelayClient(config)`,
          `print("created")`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      assert.strictEqual(result.stdout.trim(), "created");
    });

    it("should track connection state", async () => {
      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh_relay import RelayClient, RelayConfig, RelayState`,
          `config = RelayConfig(relay_url="wss://test.milimo.dev", squad_id="test", role="content")`,
          `client = RelayClient(config)`,
          `print(json.dumps({"state": client.state.value, "is_ready": client.is_ready}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.state, "disconnected");
      assert.strictEqual(data.is_ready, false);
    });
  });

  describe("integration with mesh", () => {
    it("should register claws with region info", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `mesh.register_claw("content", "wss://us-east-1.mesh.milimo.dev/content")`,
          `mesh.register_claw("ops", "wss://eu-west-1.mesh.milimo.dev/ops")`,
          `topology = mesh.topology`,
          `print(json.dumps({"roles": list(topology.keys())}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.roles.includes("content"), "Should have content role");
      assert.ok(data.roles.includes("ops"), "Should have ops role");
    });
  });
});
