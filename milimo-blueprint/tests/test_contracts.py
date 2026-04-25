# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Inter-Claw Message Contracts.

Tests cover:
- Message type validation
- Payload schema validation
- Sender/recipient role validation
- New Content Claw message types
"""

from orchestrator.contracts import (
    ClawMessage,
    ContractValidator,
    MESSAGE_TYPE_SCHEMAS,
    VALID_MESSAGE_TYPES,
    VALID_ROLES,
    VALID_RECIPIENTS,
)


class TestMessageTypes:
    """Tests for message type constants."""

    def test_valid_message_types_includes_content_claw_types(self):
        """All Content Claw message types are in VALID_MESSAGE_TYPES."""
        content_types = {
            "content_performance_query",
            "performance_signal",
            "brief_acknowledged",
            "client_health_signal",
            "revision_request",
        }
        assert content_types.issubset(VALID_MESSAGE_TYPES)

    def test_message_type_schemas_defined_for_content_claw(self):
        """MESSAGE_TYPE_SCHEMAS has definitions for Content Claw types."""
        content_types = {
            "content_performance_query",
            "performance_signal",
            "brief_acknowledged",
            "client_health_signal",
            "revision_request",
        }
        for msg_type in content_types:
            assert msg_type in MESSAGE_TYPE_SCHEMAS, f"Missing schema for {msg_type}"

    def test_brief_schema_has_required_payload_fields(self):
        """Brief message schema includes all required payload fields."""
        brief_schema = MESSAGE_TYPE_SCHEMAS["brief"]
        required = brief_schema["required_payload"]

        assert "client_id" in required
        assert "project_id" in required
        assert "brief_text" in required
        assert "deadline" in required
        assert "tone_requirements" in required
        assert "platform_targets" in required


class TestPayloadSchemaValidation:
    """Tests for _validate_payload_schema function."""

    def _create_validator(self) -> ContractValidator:
        """Create a minimal validator for testing."""
        return ContractValidator.from_dict(
            {
                "message_matrix": {
                    "ops": {"content": ["brief", "revision_request"]},
                    "content": {
                        "analytics": [
                            "content_performance_query",
                            "performance_signal",
                        ],
                        "ops": ["brief_acknowledged"],
                    },
                    "analytics": {"content": ["client_health_signal"]},
                },
                "message_types": {},
            }
        )

    def test_valid_brief_message_passes_schema_validation(self):
        """Brief message with all required fields passes validation."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="brief",
            payload={
                "client_id": "client-123",
                "project_id": "proj-456",
                "brief_text": "Create social media campaign",
                "deadline": "2026-04-01",
                "tone_requirements": {"voice": "professional"},
                "platform_targets": ["twitter", "linkedin"],
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_missing_required_payload_field_fails(self):
        """Message missing required payload field fails validation."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="brief",
            payload={
                "client_id": "client-123",
                "project_id": "proj-456",
                "brief_text": "Create social media campaign",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Missing required payload fields" in result.reason
        assert "deadline" in result.reason

    def test_wrong_sender_role_for_schema_fails(self):
        """Message from wrong sender role fails validation."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="finance",
            recipient_role="content",
            message_type="brief",
            payload={
                "client_id": "client-123",
                "project_id": "proj-456",
                "brief_text": "Create social media campaign",
                "deadline": "2026-04-01",
                "tone_requirements": {"voice": "professional"},
                "platform_targets": ["twitter"],
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Unauthorized" in result.reason or "Invalid sender" in result.reason

    def test_wrong_recipient_role_for_schema_fails(self):
        """Message to wrong recipient role fails validation."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="ops",
            recipient_role="finance",
            message_type="brief",
            payload={
                "client_id": "client-123",
                "project_id": "proj-456",
                "brief_text": "Create social media campaign",
                "deadline": "2026-04-01",
                "tone_requirements": {"voice": "professional"},
                "platform_targets": ["twitter"],
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Unauthorized" in result.reason or "Invalid recipient" in result.reason

    def test_message_type_without_schema_passes(self):
        """Message type without defined schema passes validation."""
        validator = ContractValidator.from_dict(
            {
                "message_matrix": {"ops": {"content": ["response"]}},
                "message_types": {},
            }
        )
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="response",
            payload={"data": "some response"},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True


class TestContentClawMessageTypes:
    """Tests for Content Claw specific message type validations."""

    def _create_validator(self) -> ContractValidator:
        """Create a validator with Content Claw message routes."""
        return ContractValidator.from_dict(
            {
                "message_matrix": {
                    "ops": {"content": ["brief", "revision_request"]},
                    "content": {
                        "analytics": [
                            "content_performance_query",
                            "performance_signal",
                        ],
                        "ops": ["brief_acknowledged"],
                    },
                    "analytics": {"content": ["client_health_signal"]},
                },
                "message_types": {},
            }
        )

    def test_content_performance_query_valid(self):
        """Valid content_performance_query message passes."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="content",
            recipient_role="analytics",
            message_type="content_performance_query",
            payload={"query": "weekly_engagement"},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_performance_signal_valid(self):
        """Valid performance_signal message passes."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="content",
            recipient_role="analytics",
            message_type="performance_signal",
            payload={
                "post_id": "post-123",
                "platform": "twitter",
                "engagement_data": {"likes": 100, "retweets": 50},
                "publish_time": "2026-03-21T10:00:00Z",
                "content_type": "text",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_brief_acknowledged_valid(self):
        """Valid brief_acknowledged message passes."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="content",
            recipient_role="ops",
            message_type="brief_acknowledged",
            payload={
                "project_id": "proj-456",
                "estimated_first_draft_time": "2026-03-22T10:00:00Z",
                "acknowledged_at": "2026-03-21T09:00:00Z",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_client_health_signal_valid(self):
        """Valid client_health_signal message passes."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="analytics",
            recipient_role="content",
            message_type="client_health_signal",
            payload={
                "client_id": "client-123",
                "health_score": 85,
                "recommended_action": "increase_posting_frequency",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_revision_request_valid(self):
        """Valid revision_request message passes."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="revision_request",
            payload={
                "project_id": "proj-456",
                "draft_id": "draft-789",
                "revision_notes": "Please make tone more casual",
                "deadline": "2026-03-23",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is True

    def test_performance_signal_missing_required_field(self):
        """performance_signal missing required field fails."""
        validator = self._create_validator()
        message = ClawMessage(
            sender_role="content",
            recipient_role="analytics",
            message_type="performance_signal",
            payload={
                "post_id": "post-123",
                "platform": "twitter",
            },
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Missing required payload fields" in result.reason


class TestContractValidatorBasics:
    """Tests for ContractValidator basic functionality."""

    def test_invalid_sender_role_rejected(self):
        """Message from invalid sender role is rejected."""
        validator = ContractValidator.from_dict(
            {
                "message_matrix": {},
                "message_types": {},
            }
        )
        message = ClawMessage(
            sender_role="invalid_role",
            recipient_role="content",
            message_type="brief",
            payload={},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Invalid sender role" in result.reason

    def test_invalid_recipient_role_rejected(self):
        """Message to invalid recipient role is rejected."""
        validator = ContractValidator.from_dict(
            {
                "message_matrix": {},
                "message_types": {},
            }
        )
        message = ClawMessage(
            sender_role="ops",
            recipient_role="invalid_role",
            message_type="brief",
            payload={},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Invalid recipient role" in result.reason

    def test_invalid_message_type_rejected(self):
        """Message with invalid type is rejected."""
        validator = ContractValidator.from_dict(
            {
                "message_matrix": {"ops": {"content": ["brief"]}},
                "message_types": {},
            }
        )
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="invalid_type",
            payload={},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Invalid message type" in result.reason

    def test_unauthorized_route_rejected(self):
        """Message not in matrix is rejected."""
        validator = ContractValidator.from_dict(
            {
                "message_matrix": {"ops": {"analytics": ["brief"]}},
                "message_types": {},
            }
        )
        message = ClawMessage(
            sender_role="ops",
            recipient_role="content",
            message_type="brief",
            payload={},
            squad_id="test-squad",
        )

        result = validator.validate(message)

        assert result.valid is False
        assert "Unauthorized" in result.reason

    def test_war_room_valid_recipient(self):
        """War room is a valid recipient but not a sender."""
        assert "war_room" in VALID_RECIPIENTS
        assert "war_room" not in VALID_ROLES


class TestSchemaMetadata:
    """Tests for schema metadata fields."""

    def test_brief_schema_has_frequency(self):
        """Brief schema has frequency metadata."""
        assert MESSAGE_TYPE_SCHEMAS["brief"]["frequency"] == "on_event"

    def test_content_performance_query_has_schedule(self):
        """content_performance_query has schedule metadata."""
        schema = MESSAGE_TYPE_SCHEMAS["content_performance_query"]
        assert schema["frequency"] == "weekly"
        assert schema["schedule"] == "monday_06:00"

    def test_brief_acknowledged_has_sla(self):
        """brief_acknowledged has SLA metadata."""
        schema = MESSAGE_TYPE_SCHEMAS["brief_acknowledged"]
        assert "sla_minutes" in schema
        assert schema["sla_minutes"] == 5

    def test_message_priorities_defined(self):
        """Message schemas have priority metadata."""
        for msg_type, schema in MESSAGE_TYPE_SCHEMAS.items():
            assert "priority" in schema, f"{msg_type} missing priority"
