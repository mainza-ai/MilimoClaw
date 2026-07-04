# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the Milimo Claw Squad Mesh Protocol.

Tests cover:
  - Contract validation (valid/invalid messages, matrix enforcement)
  - Mesh coordinator (registration, routing, health monitoring)
  - Message queuing and delivery
"""

import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.contracts import ClawMessage, ContractValidator
from orchestrator.mesh import MeshCoordinator

CONFIG_PATH = Path(__file__).parent.parent / "mesh_config.yaml"


# ── Contract Validation Tests ─────────────────────────────────────────


class TestContractValidation(unittest.TestCase):
    """Test message contract validation against the mesh config matrix."""

    @classmethod
    def setUpClass(cls):
        cls.validator = ContractValidator.from_config_file(CONFIG_PATH)

    def _msg(self, sender, recipient, msg_type, payload=None):
        # Provide default payloads with required fields for message types that have schemas
        default_payloads = {
            "brief": {
                "client_id": "client-001",
                "project_id": "proj-001",
                "brief_text": "Test brief content",
                "deadline": "2026-04-01",
                "tone_requirements": "professional",
                "platform_targets": ["linkedin"],
            },
            "deliverable": {
                "type": "content",
                "urls": ["https://example.com/post"],
            },
            "query": {
                "query": "test query",
            },
            "response": {
                "data": "test response data",
            },
            "signal": {
                "signal_type": "test_signal",
                "message": "Test signal message",
            },
            "summary": {
                "summary_type": "weekly",
                "data": {},
            },
            "finance_summary": {
                "week_revenue": 1000.0,
            },
            "draft_ready": {
                "draft_id": "draft-001",
                "platform": "linkedin",
                "content_type": "post",
            },
        }
        if payload is None:
            payload = default_payloads.get(msg_type, {})
        return ClawMessage(
            sender_role=sender,
            recipient_role=recipient,
            message_type=msg_type,
            payload=payload,
            squad_id="test-squad",
        )

    # --- Valid messages ---

    def test_ops_can_send_brief_to_content(self):
        result = self.validator.validate(self._msg("ops", "content", "brief"))
        self.assertTrue(result.valid)

    def test_content_can_send_deliverable_to_ops(self):
        result = self.validator.validate(self._msg("content", "ops", "deliverable"))
        self.assertTrue(result.valid)

    def test_content_can_send_query_to_analytics(self):
        result = self.validator.validate(self._msg("content", "analytics", "query"))
        self.assertTrue(result.valid)

    def test_analytics_can_send_summary_to_content(self):
        result = self.validator.validate(self._msg("analytics", "content", "summary"))
        self.assertTrue(result.valid)

    def test_finance_can_send_signal_to_ops(self):
        result = self.validator.validate(self._msg("finance", "ops", "signal"))
        self.assertTrue(result.valid)

    def test_ops_can_send_signal_to_war_room(self):
        result = self.validator.validate(self._msg("ops", "war_room", "signal"))
        self.assertTrue(result.valid)

    # --- Invalid role ---

    def test_invalid_sender_role_rejected(self):
        result = self.validator.validate(self._msg("hacker", "ops", "brief"))
        self.assertFalse(result.valid)
        self.assertIn("Invalid sender", result.reason)

    def test_invalid_recipient_role_rejected(self):
        result = self.validator.validate(self._msg("ops", "hacker", "brief"))
        self.assertFalse(result.valid)
        self.assertIn("Invalid recipient", result.reason)

    # --- Invalid message type ---

    def test_invalid_message_type_rejected(self):
        result = self.validator.validate(self._msg("ops", "content", "attack"))
        self.assertFalse(result.valid)
        self.assertIn("Invalid message type", result.reason)

    # --- Unauthorized routes ---

    def test_content_cannot_send_brief_to_finance(self):
        """Content has no outbound route to Finance."""
        result = self.validator.validate(self._msg("content", "finance", "brief"))
        self.assertFalse(result.valid)
        self.assertIn("Unauthorized", result.reason)

    def test_finance_cannot_send_brief_to_content(self):
        """Finance has no brief route to Content."""
        result = self.validator.validate(self._msg("finance", "content", "brief"))
        self.assertFalse(result.valid)

    def test_analytics_cannot_send_deliverable_to_content(self):
        """Analytics sends summary/response to Content, not deliverable."""
        result = self.validator.validate(
            self._msg("analytics", "content", "deliverable")
        )
        self.assertFalse(result.valid)

    # --- Utility methods ---

    def test_deliverable_requires_approval(self):
        self.assertTrue(self.validator.requires_approval("deliverable"))

    def test_query_does_not_require_approval(self):
        self.assertFalse(self.validator.requires_approval("query"))

    def test_get_allowed_types(self):
        types = self.validator.get_allowed_types("ops", "content")
        self.assertIn("brief", types)
        self.assertIn("project_brief", types)

    def test_get_all_senders_for_war_room(self):
        senders = self.validator.get_all_senders_for("war_room")
        # All roles should be able to reach war_room
        for role in ["content", "ops", "analytics", "finance"]:
            self.assertIn(role, senders)


# ── Mesh Coordinator Tests ────────────────────────────────────────────


class TestMeshCoordinator(unittest.TestCase):
    """Test the squad mesh coordinator."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="milimo-mesh-test-")
        self.mesh = MeshCoordinator.from_config_file(
            CONFIG_PATH, squad_id="test-squad", mesh_dir=self.tmp_dir
        )

    def tearDown(self):
        self.mesh.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _msg(self, sender, recipient, msg_type, payload=None):
        # Provide default payloads with required fields
        default_payloads = {
            "brief": {
                "client_id": "client-001",
                "project_id": "proj-001",
                "brief_text": "Test brief content",
                "deadline": "2026-04-01",
                "tone_requirements": "professional",
                "platform_targets": ["linkedin"],
            },
            "deliverable": {
                "type": "content",
                "urls": ["https://example.com/post"],
            },
            "signal": {
                "signal_type": "test_signal",
                "message": "Test signal",
            },
        }
        if payload is None:
            payload = default_payloads.get(msg_type, {})
        return ClawMessage(
            sender_role=sender,
            recipient_role=recipient,
            message_type=msg_type,
            payload=payload,
            squad_id="test-squad",
        )

    # --- Registration ---

    def test_register_claw(self):
        self.mesh.register_claw("content", "local://content")
        self.assertIn("content", self.mesh.topology)

    def test_multiple_registrations(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        self.assertEqual(len(self.mesh.topology), 2)

    def test_unregister_claw(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.unregister_claw("content")
        self.assertNotIn("content", self.mesh.topology)

    def test_get_online_claws(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        self.assertEqual(sorted(self.mesh.get_online_claws()), ["content", "ops"])

    # --- Message Routing ---

    def test_send_valid_message(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")

        result = self.mesh.send_message(self._msg("ops", "content", "brief"))
        self.assertTrue(result.delivered)

    def test_send_to_unregistered_recipient(self):
        self.mesh.register_claw("ops", "local://ops")
        result = self.mesh.send_message(self._msg("ops", "content", "brief"))
        self.assertFalse(result.delivered)
        self.assertIn("not registered", result.reason)

    def test_send_invalid_contract(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("finance", "local://finance")
        result = self.mesh.send_message(self._msg("content", "finance", "brief"))
        self.assertFalse(result.delivered)
        self.assertIn("Unauthorized", result.reason)

    def test_deliverable_flagged_for_approval(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        result = self.mesh.send_message(self._msg("content", "ops", "deliverable"))
        self.assertTrue(result.delivered)
        self.assertTrue(result.requires_approval)

    def test_war_room_always_reachable(self):
        """War room doesn't need registration — it's always available."""
        self.mesh.register_claw("ops", "local://ops")
        result = self.mesh.send_message(self._msg("ops", "war_room", "signal"))
        self.assertTrue(result.delivered)

    def test_pending_messages_appear_in_inbox(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        # Use _msg without payload override to get proper defaults
        self.mesh.send_message(self._msg("ops", "content", "brief"))
        self.mesh.drain_outbox()
        pending = self.mesh.get_pending_messages("content")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["message_type"], "brief")

    # --- Health Monitoring ---

    def test_heartbeat(self):
        self.mesh.register_claw("content", "local://content")
        self.assertTrue(self.mesh.heartbeat("content"))
        node = self.mesh.topology["content"]
        self.assertNotEqual(node.last_heartbeat, "")

    def test_mark_unhealthy(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.mark_unhealthy("content")
        node = self.mesh.topology["content"]
        self.assertEqual(node.status, "unhealthy")

    def test_heartbeat_recovers_unhealthy(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.mark_unhealthy("content")
        self.mesh.heartbeat("content")
        node = self.mesh.topology["content"]
        self.assertEqual(node.status, "online")

    def test_offline_claw_rejects_messages(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        self.mesh.set_status("content", "offline")
        result = self.mesh.send_message(self._msg("ops", "content", "brief"))
        self.assertFalse(result.delivered)

    def test_finals_mode_allows_messages(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("ops", "local://ops")
        self.mesh.set_status("content", "finals-mode")
        result = self.mesh.send_message(self._msg("ops", "content", "brief"))
        self.assertTrue(result.delivered)

    # --- Topology Persistence ---

    def test_topology_persists_to_disk(self):
        self.mesh.register_claw("content", "local://content")
        topo_file = Path(self.tmp_dir) / "topology.json"
        self.assertTrue(topo_file.exists())
        topo = json.loads(topo_file.read_text())
        self.assertIn("content", topo["nodes"])

    def test_rejected_messages_logged(self):
        self.mesh.register_claw("content", "local://content")
        self.mesh.register_claw("finance", "local://finance")
        self.mesh.send_message(self._msg("content", "finance", "brief"))
        rejected_dir = Path(self.tmp_dir) / "rejected"
        rejected_files = list(rejected_dir.glob("*.json"))
        self.assertGreater(len(rejected_files), 0)


class TestTransportContractVerification(unittest.TestCase):
    """Test message contract verification inside transport adapters."""

    @patch("orchestrator.gateway_adapter.mesh_dir")
    def test_file_based_gateway_contract_verification(self, mock_mesh_dir):
        import tempfile
        import shutil
        from unittest.mock import patch
        from orchestrator.gateway_adapter import FileBasedGateway, GatewayConfig

        # Set up isolated temp directory
        tmp_dir = Path(tempfile.mkdtemp(prefix="milimo-gateway-test-"))
        mock_mesh_dir.return_value = tmp_dir

        try:
            # Load validator
            validator = ContractValidator.from_config_file(CONFIG_PATH)

            config = GatewayConfig(
                endpoint="file://",
                mesh_secret="test-secret",
                squad_id="test-squad",
                role="ops",
                validator=validator,
            )

            gateway = FileBasedGateway(config)
            gateway.connect()

            # 1. Send invalid message type (should be rejected/dropped on send)
            invalid_msg = {
                "message_id": "msg-invalid-type",
                "sender_role": "ops",
                "recipient_role": "content",
                "message_type": "invalid_type_name_xyz",
                "payload": {},
                "timestamp": "2026-07-03T18:00:00Z",
            }
            res = gateway.send(invalid_msg)
            self.assertFalse(res.success)
            self.assertEqual(res.error_code, "CONTRACT_VIOLATION")

            # 2. Send unauthorized route: content -> finance brief (should be rejected)
            unauth_msg = {
                "message_id": "msg-unauth-route",
                "sender_role": "content",
                "recipient_role": "finance",
                "message_type": "brief",
                "payload": {
                    "client_id": "client-456",
                    "project_id": "proj-123",
                    "brief_text": "hello",
                    "deadline": "2026-07-10",
                    "tone_requirements": "casual",
                    "platform_targets": ["twitter"]
                },
                "timestamp": "2026-07-03T18:00:00Z",
            }
            res = gateway.send(unauth_msg)
            self.assertFalse(res.success)
            self.assertEqual(res.error_code, "CONTRACT_VIOLATION")

            # 3. Simulate receiving an invalid/unauthorized message in inbox
            # Write directly to inbox file
            inbox_dir = gateway._inbox
            self.assertIsNotNone(inbox_dir)
            invalid_inbox_file = inbox_dir / "2026-07-03T18-00-00Z_msg-unauth-route.json"

            # Write unauth_msg dict to file
            invalid_inbox_file.write_text(json.dumps(unauth_msg))

            # receive should drop/ignore the invalid message
            messages = gateway.receive(limit=10)
            self.assertEqual(len(messages), 0)

            # Clean up
            gateway.close()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_mesh_secret_production_block(self):
        """Verify that MeshCoordinator blocks startup in non-dev env if mesh_secret is empty."""
        import os
        from orchestrator.mesh import MeshConfig

        # Save original env
        orig_env = os.environ.get("MILIMO_ENV")

        try:
            # Set environment to production
            os.environ["MILIMO_ENV"] = "production"

            # Setup config with empty secret
            config = MeshConfig(mesh_secret="")
            validator = ContractValidator.from_dict({"message_matrix": {}, "message_types": {}})

            with self.assertRaises(ValueError) as ctx:
                MeshCoordinator(validator=validator, mesh_config=config)

            self.assertIn("mesh_secret", str(ctx.exception))
            self.assertIn("production environment", str(ctx.exception))

            # Should succeed if environment is set to development/dev
            os.environ["MILIMO_ENV"] = "development"
            mesh = MeshCoordinator(validator=validator, mesh_config=config)
            self.assertIsNotNone(mesh)

        finally:
            # Restore environment
            if orig_env is None:
                os.environ.pop("MILIMO_ENV", None)
            else:
                os.environ["MILIMO_ENV"] = orig_env

    def _msg(self, sender, recipient, msg_type, payload=None):
        default_payloads = {
            "brief": {
                "client_id": "client-001",
                "project_id": "proj-001",
                "brief_text": "Test brief content",
                "deadline": "2026-04-01",
                "tone_requirements": "professional",
                "platform_targets": ["linkedin"],
            },
        }
        if payload is None:
            payload = default_payloads.get(msg_type, {})
        return ClawMessage(
            sender_role=sender,
            recipient_role=recipient,
            message_type=msg_type,
            payload=payload,
            squad_id="test-squad",
        )

    def test_outbox_queue_drain_on_reconnect(self):
        """Verify that the background outbox processor queues messages when gateway is down, and drains them when gateway is restored."""
        import tempfile
        import shutil
        import time
        from unittest.mock import MagicMock
        from orchestrator.gateway_adapter import ConnectionState, SendResult

        tmp_dir = Path(tempfile.mkdtemp(prefix="milimo-outbox-test-"))
        try:
            # 1. Setup MeshCoordinator with a custom mock gateway
            validator = ContractValidator.from_config_file(CONFIG_PATH)
            mesh = MeshCoordinator(validator=validator, squad_id="test-squad", mesh_dir=tmp_dir)

            # Create mock gateway
            mock_gateway = MagicMock()
            mock_gateway.state = ConnectionState.CONNECTED

            # Initially, gateway returns failure/error
            mock_gateway.send.return_value = SendResult(
                success=False, error_code="E500", error_message="Network Down"
            )
            mesh._gateway = mock_gateway

            # Register claws
            mesh.register_claw("content", "local://content")
            mesh.register_claw("ops", "local://ops")

            # 2. Send message while gateway is failing
            msg = self._msg("ops", "content", "brief")
            result = mesh.send_message(msg)
            self.assertTrue(result.delivered)  # True because it queued in outbox successfully

            # Check that it exists in outbox folder
            time.sleep(0.1)
            outbox_files = list(mesh._outbox_dir.glob("*.json"))
            self.assertEqual(len(outbox_files), 1)

            # 3. Restore gateway: now it returns success
            mock_gateway.send.return_value = SendResult(
                success=True, message_id=msg.message_id, requires_approval=False
            )

            # Wait/drain the outbox
            mesh.drain_outbox()

            # Outbox should be completely empty now!
            outbox_files = list(mesh._outbox_dir.glob("*.json"))
            self.assertEqual(len(outbox_files), 0)

            # Verify gateway was called
            self.assertTrue(mock_gateway.send.called)

            mesh.close()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_parallel_execution_pool(self) -> None:
        """Verify that sessions_spawn processes multiple tasks concurrently."""
        from orchestrator.mesh import sessions_spawn
        from milimo_core.protocols.delegation import ClawTask

        tasks = [
            ClawTask(claw="content", goal="Generate a blog post about Antigravity"),
            ClawTask(claw="ops", goal="Analyze deadline risks for active sprints"),
            ClawTask(claw="build", goal="Run dependency audit on current workspace"),
        ]

        results = sessions_spawn(tasks, max_workers=3)

        self.assertEqual(len(results), 3)
        for res in results:
            self.assertTrue(res.success)
            self.assertIsNotNone(res.output)
            self.assertEqual(res.output["claw"], res.claw)
            self.assertIn("Successfully completed goal", res.output["response"])


if __name__ == "__main__":
    unittest.main()
