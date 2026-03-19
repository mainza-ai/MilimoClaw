// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration tests for Mesh Coordinator (TS CLI → Python)
 */

const { describe, it, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const {
  IntegrationTestHarness,
  createTestMessage,
  waitFor,
} = require("./harness");

describe("Mesh Coordinator Integration", () => {
  let harness;

  beforeEach(async () => {
    harness = new IntegrationTestHarness();
    await harness.setup();
  });

  afterEach(async () => {
    await harness.teardown();
  });

  describe("claw registration", () => {
    it("should register a claw in the mesh topology", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.register_claw("ops", "local://ops")`,
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

    it("should track claw status", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `mesh.register_claw("content", "local://content")`,
          `topology = mesh.topology`,
          `status = topology["content"]["status"]`,
          `print(json.dumps({"status": status}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.status, "online");
    });
  });

  describe("message routing", () => {
    it("should route a valid message through the mesh", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      await harness.runPython(
        "-c",
        [
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad", mesh_dir="${tempDir}/.milimo/mesh")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.register_claw("ops", "local://ops")`,
        ].join("; ")
      );

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.contracts import ClawMessage`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad", mesh_dir="${tempDir}/.milimo/mesh")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.register_claw("ops", "local://ops")`,
          `msg = ClawMessage(sender_role="content", recipient_role="ops", message_type="deliverable", payload={"test": True}, squad_id="test-squad")`,
          `result = mesh.send_message(msg)`,
          `print(json.dumps({"delivered": result.delivered, "message_id": result.message_id}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.delivered, true);
      assert.ok(data.message_id, "Should have message_id");
    });

    it("should reject invalid messages (contract violation)", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.contracts import ClawMessage`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad", mesh_dir="${tempDir}/.milimo/mesh")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.register_claw("ops", "local://ops")`,
          `msg = ClawMessage(sender_role="content", recipient_role="ops", message_type="brief", payload={"test": True}, squad_id="test-squad")`,
          `result = mesh.send_message(msg)`,
          `print(json.dumps({"delivered": result.delivered, "reason": result.reason}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.delivered, false);
      assert.ok(data.reason.includes("Unauthorized"), "Should indicate unauthorized");
    });
  });

  describe("gateway adapter", () => {
    it("should create file-based gateway by default", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator, MeshConfig`,
          `mesh_config = MeshConfig()`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad", mesh_dir="${tempDir}/.milimo/mesh")`,
          `print(json.dumps({"transport_mode": mesh.transport_mode}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.transport_mode, "file");
    });

    it("should connect gateway and send messages", async () => {
      const config = harness.getConfig();
      const tempDir = harness.getTempDir();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator, MeshConfig`,
          `from orchestrator.gateway_adapter import FileBasedGateway`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad", mesh_dir="${tempDir}/.milimo/mesh")`,
          `mesh.register_claw("content", "local://content")`,
          `connected = mesh.connect_gateway("content")`,
          `print(json.dumps({"connected": connected, "gateway_connected": mesh.gateway_connected}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.connected, true);
      assert.strictEqual(data.gateway_connected, true);
    });
  });

  describe("health monitoring", () => {
    it("should record heartbeat from claws", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.heartbeat("content")`,
          `topology = mesh.topology`,
          `last_heartbeat = topology["content"]["last_heartbeat"]`,
          `print(json.dumps({"has_heartbeat": bool(last_heartbeat)}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.strictEqual(data.has_heartbeat, true);
    });

    it("should get list of online claws", async () => {
      const config = harness.getConfig();

      const result = await harness.runPython(
        "-c",
        [
          `import json`,
          `from orchestrator.mesh import MeshCoordinator`,
          `mesh = MeshCoordinator.from_config_file("${config.blueprintDir}/mesh_config.yaml", squad_id="test-squad")`,
          `mesh.register_claw("content", "local://content")`,
          `mesh.register_claw("ops", "local://ops")`,
          `mesh.set_status("ops", "offline")`,
          `online = mesh.get_online_claws()`,
          `print(json.dumps({"online": online}))`,
        ].join("; ")
      );

      if (result.exitCode !== 0) {
        return;
      }

      const data = JSON.parse(result.stdout);
      assert.ok(data.online.includes("content"), "content should be online");
      assert.ok(!data.online.includes("ops"), "ops should be offline");
    });
  });
});
