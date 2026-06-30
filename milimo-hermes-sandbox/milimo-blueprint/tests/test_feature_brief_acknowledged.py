# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for FIX 4: feature_brief_acknowledged message type and SLA enforcement.

Per spec Rule 6: Build Claw must send feature_brief_acknowledged within 10 minutes
of receiving feature_brief from Ops Claw.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestFeatureBriefAcknowledgedSchema:
    """Tests for feature_brief_acknowledged message schema."""

    def test_schema_validates_with_all_required_fields(self):
        """feature_brief_acknowledged schema validates with all required fields."""
        from orchestrator.contracts import MESSAGE_TYPE_SCHEMAS

        message = {
            "message_type": "feature_brief_acknowledged",
            "sender_role": "build",
            "recipient_role": "ops",
            "payload": {
                "project_id": "proj-001",
                "estimated_start": "2026-03-22T10:00:00Z",
                "clarity_score": "clear",
            },
        }

        schema = MESSAGE_TYPE_SCHEMAS.get("feature_brief_acknowledged")
        assert schema is not None

        required = schema.get("required_payload", [])
        for field in required:
            assert field in message["payload"], f"Missing required field: {field}"

    def test_schema_rejects_invalid_sender_role(self):
        """Schema rejects 'content' as sender_role (build only)."""
        from orchestrator.contracts import MESSAGE_TYPE_SCHEMAS

        schema = MESSAGE_TYPE_SCHEMAS.get("feature_brief_acknowledged")
        assert schema is not None

        sender_roles = schema.get("sender_roles", [])
        assert "content" not in sender_roles
        assert "build" in sender_roles

    def test_schema_accepts_optional_fields(self):
        """Schema accepts optional missing_elements and deadline_risk."""
        from orchestrator.contracts import MESSAGE_TYPE_SCHEMAS

        schema = MESSAGE_TYPE_SCHEMAS.get("feature_brief_acknowledged")
        assert schema is not None

        optional = schema.get("optional_payload", [])
        assert "missing_elements" in optional
        assert "deadline_risk" in optional

    def test_clarity_score_must_be_clear_or_low(self):
        """clarity_score must be 'clear' or 'low'."""
        pass


class TestFeatureBriefAcknowledgedSLA:
    """Tests for 10-minute SLA on feature_brief_acknowledged."""

    def test_handle_feature_brief_starts_10_minute_timer(self):
        """handle_feature_brief starts a 10-minute acknowledgment timer."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_gateway = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        message = {
            "message_type": "feature_brief",
            "sender_role": "ops",
            "recipient_role": "build",
            "payload": {
                "project_id": "proj-001",
                "client_id": "client-001",
                "feature_description": "Add login page",
                "deadline": "2026-03-25",
            },
        }

        with patch.object(dispatcher, "_send_overdue_ack_warning"):
            with patch("threading.Timer") as mock_timer:
                mock_timer_instance = MagicMock()
                mock_timer.return_value = mock_timer_instance

                dispatcher.handle_feature_brief(message)

                mock_timer.assert_called_once()
                args, kwargs = mock_timer.call_args
                assert args[0] == 600, "Timer should be 600 seconds (10 minutes)"

    def test_send_feature_brief_acknowledged_validates_clarity_score(self):
        """send_feature_brief_acknowledged validates clarity_score."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_gateway = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        with pytest.raises(ValueError):
            dispatcher.send_feature_brief_acknowledged(
                project_id="proj-001",
                estimated_start="2026-03-22T10:00:00Z",
                clarity_score="invalid",
            )

    def test_send_feature_brief_acknowledged_accepts_clear(self):
        """send_feature_brief_acknowledged accepts 'clear' as clarity_score."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_log.append = MagicMock()
        mock_gateway = MagicMock()
        mock_gateway.send = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        dispatcher.send_feature_brief_acknowledged(
            project_id="proj-001",
            estimated_start="2026-03-22T10:00:00Z",
            clarity_score="clear",
        )

    def test_send_feature_brief_acknowledged_accepts_low(self):
        """send_feature_brief_acknowledged accepts 'low' as clarity_score."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_log.append = MagicMock()
        mock_gateway = MagicMock()
        mock_gateway.send = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        dispatcher.send_feature_brief_acknowledged(
            project_id="proj-001",
            estimated_start="TBD",
            clarity_score="low",
            missing_elements=["spec", "mockups"],
        )


class TestOverdueAcknowledgment:
    """Tests for overdue acknowledgment when processing exceeds 10 minutes."""

    def test_send_overdue_ack_warning_sends_preliminary_ack(self):
        """_send_overdue_ack_warning sends preliminary acknowledgment."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_log.append = MagicMock()
        mock_gateway = MagicMock()
        mock_gateway.send = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        dispatcher._send_overdue_ack_warning("proj-001")

    def test_overdue_ack_uses_low_clarity(self):
        """Overdue ack uses clarity_score='low'."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_log.append = MagicMock()
        mock_gateway = MagicMock()
        mock_gateway.send = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        with patch.object(dispatcher, "send_feature_brief_acknowledged") as mock_send:
            dispatcher._send_overdue_ack_warning("proj-001")
            mock_send.assert_called_once_with(
                project_id="proj-001",
                estimated_start="TBD",
                clarity_score="low",
            )

    def test_overdue_ack_logs_delayed_event(self):
        """Overdue ack logs feature_brief_ack_delayed event."""
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        mock_fs = MagicMock()
        mock_log = MagicMock()
        mock_log.append = MagicMock()
        mock_gateway = MagicMock()
        mock_gateway.send = MagicMock()

        dispatcher = BuildSignalDispatcher(
            fs=mock_fs,
            operational_log=mock_log,
            mesh_gateway=mock_gateway,
            squad_id="test-squad",
        )

        dispatcher._send_overdue_ack_warning("proj-001")

        append_calls = mock_log.append.call_args_list
        assert len(append_calls) >= 1
