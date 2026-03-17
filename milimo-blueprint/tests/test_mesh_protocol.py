#!/usr/bin/env python3
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
import os
import shutil
import sys
import tempfile
import unittest
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
        return ClawMessage(
            sender_role=sender,
            recipient_role=recipient,
            message_type=msg_type,
            payload=payload or {},
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
        self.assertIn("signal", types)

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
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _msg(self, sender, recipient, msg_type, payload=None):
        return ClawMessage(
            sender_role=sender,
            recipient_role=recipient,
            message_type=msg_type,
            payload=payload or {},
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
        result = self.mesh.send_message(
            self._msg("content", "ops", "deliverable")
        )
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
        self.mesh.send_message(
            self._msg("ops", "content", "brief", {"project": "test"})
        )
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


if __name__ == "__main__":
    unittest.main()
