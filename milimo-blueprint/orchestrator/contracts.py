#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Inter-Claw Message Contracts

Typed message contract definitions for squad mesh communication.
Each message is validated against the sender's outbound policy and
the recipient's inbound policy before delivery. Invalid messages
are dropped and logged.

Usage:
    from contracts import ContractValidator, ClawMessage

    validator = ContractValidator.from_config_file("mesh_config.yaml")
    msg = ClawMessage(
        sender_role="ops",
        recipient_role="content",
        message_type="brief",
        payload={"project_id": "abc", "scope": "Social campaign"},
        squad_id="my-squad",
    )
    result = validator.validate(msg)
    # result.valid == True
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("milimo.contracts")

# Valid claw roles
VALID_ROLES = {"content", "ops", "analytics", "finance", "build", "assistant"}
# Assistant role (also a valid claw role)
ASSISTANT_ROLE = "assistant"
VALID_SENDERS = VALID_ROLES  # assistant already in VALID_ROLES
# War room is a valid recipient but not a sender role
VALID_RECIPIENTS = VALID_ROLES | {"war_room"}  # assistant already in VALID_ROLES

# Valid message types
VALID_MESSAGE_TYPES = {
    "brief",
    "query",
    "response",
    "signal",
    "deliverable",
    "summary",
    "finance_summary",
    # Content Claw message types
    "draft_ready",
    "content_performance_query",
    "performance_signal",
    "brief_acknowledged",
    "deliverable_complete",
    "client_health_signal",
    "client_health_signal_ops",
    "revision_request",
    # Build Claw message types
    "feature_brief",
    "feature_brief_acknowledged",
    "deploy_complete",
    "shipping_summary",
    "behavior_query",
    # Analytics Claw message types
    "performance_intel",
    "retention_signals",
    "revenue_anomaly",
    "client_health_alert",
    "content_performance_response",
    "behavior_query_response",
    # Finance Claw message types
    "pricing_query",
    "pricing_response",
    "invoice_ready",
    "payment_overdue",
    "project_complete",
    # Ops Claw message types
    "project_brief",
    "client_onboarded",
    # Finance → Analytics
    "revenue_summary",
    # Tool proposal
    "tool_proposal",
    # Finance → War Room: Overdue payment alert
    "overdue_alert",
    # Assistant message types
    "assistant_query",
    "assistant_task",
    "assistant_response",
}

# Message types that require War Room approval (AUTO priority by default)
AUTO_APPROVAL_TYPES = {"finance_summary"}

# Message type schemas for validation
MESSAGE_TYPE_SCHEMAS: dict[str, dict[str, Any]] = {
    # Content → War Room: Draft ready for review
    "draft_ready": {
        "sender_roles": ["content"],
        "recipient_roles": ["war_room"],
        "required_payload": ["draft_id", "platform", "content_type"],
        "optional_payload": [
            "client_id",
            "project_id",
            "brief_id",
            "approval_probability",
            "variants_count",
            "tone",
            "scheduled_time",
            "has_variant_b",
        ],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Existing brief type - updated with full spec payload
    "brief": {
        "sender_roles": ["ops"],
        "recipient_roles": ["content"],
        "required_payload": [
            "client_id",
            "project_id",
            "brief_text",
            "deadline",
            "tone_requirements",
            "platform_targets",
        ],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Content → Ops: Deliverable complete
    "deliverable_complete": {
        "sender_roles": ["content"],
        "recipient_roles": ["ops"],
        "required_payload": ["project_id", "published_urls"],
        "optional_payload": [
            "brief_id",
            "client_id",
            "performance_baseline",
            "completed_at",
        ],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Content → Analytics: Weekly performance query
    "content_performance_query": {
        "sender_roles": ["content"],
        "recipient_roles": ["analytics"],
        "required_payload": ["query"],
        "optional_payload": ["lookback_days", "platform"],
        "frequency": "weekly",
        "schedule": "monday_06:00",
        "priority": "AUTO",
    },
    # Content → Analytics: Post-publish performance signal
    "performance_signal": {
        "sender_roles": ["content"],
        "recipient_roles": ["analytics"],
        "required_payload": [
            "post_id",
            "platform",
            "engagement_data",
            "publish_time",
            "content_type",
        ],
        "optional_payload": ["client_id"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Content → Ops: Brief acknowledgment
    "brief_acknowledged": {
        "sender_roles": ["content"],
        "recipient_roles": ["ops"],
        "required_payload": [
            "project_id",
            "estimated_first_draft_time",
            "acknowledged_at",
        ],
        "frequency": "on_event",
        "sla_minutes": 5,
        "priority": "REVIEW",
    },
    # Ops/Analytics → Content: Client health signal
    "client_health_signal": {
        "sender_roles": ["ops", "analytics"],
        "recipient_roles": ["content"],
        "required_payload": ["client_id", "health_score", "recommended_action"],
        "optional_payload": ["health_factors", "signals"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Ops → Content: Revision request
    "revision_request": {
        "sender_roles": ["ops"],
        "recipient_roles": ["content"],
        "required_payload": ["project_id", "draft_id", "revision_notes", "deadline"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Finance → War Room: Revenue summary for widget
    "finance_summary": {
        "sender_roles": ["finance"],
        "recipient_roles": ["war_room"],
        "required_payload": ["week_revenue"],
        "optional_payload": [
            "week_over_week_pct",
            "invoices_paid",
            "invoices_pending",
            "last_updated",
        ],
        "frequency": "on_change",
        "priority": "AUTO",
    },
    # Build → Ops: Deploy complete
    "deploy_complete": {
        "sender_roles": ["build"],
        "recipient_roles": ["ops"],
        "required_payload": ["deploy_id", "project_id"],
        "optional_payload": ["version", "deployed_at", "environment"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Build → Content: Shipping summary (for devlog)
    "shipping_summary": {
        "sender_roles": ["build"],
        "recipient_roles": ["content"],
        "required_payload": ["summary"],
        "optional_payload": ["features", "fixes", "week_end"],
        "frequency": "weekly",
        "priority": "AUTO",
    },
    # Analytics → Content: Performance intelligence
    "performance_intel": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["content"],
        "required_payload": ["report_id"],
        "optional_payload": ["top_performers", "recommendations", "week_end"],
        "frequency": "weekly",
        "priority": "AUTO",
    },
    # Analytics → Build: Retention signals
    "retention_signals": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["build"],
        "required_payload": ["signal_type"],
        "optional_payload": ["feature_id", "correlation", "recommendation"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Ops/Analytics → Ops: Client health signal (Ops receives from Analytics)
    "client_health_signal_ops": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["ops"],
        "required_payload": ["client_id", "health_score"],
        "optional_payload": ["recommended_action", "signals"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Analytics → Ops: Client health alert (IMMEDIATE when score < 6.0)
    "client_health_alert": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["ops"],
        "required_payload": ["client_id", "health_score", "alert_type"],
        "optional_payload": ["recommended_action", "signals", "triggered_at"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Analytics → Content: Content performance response (2-min SLA)
    "content_performance_response": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["content"],
        "required_payload": ["query_id", "results"],
        "optional_payload": ["top_performers", "recommendations", "response_time_ms"],
        "frequency": "on_event",
        "sla_minutes": 2,
        "priority": "AUTO",
    },
    # Analytics → Build: Behavior query response (2-min SLA)
    "behavior_query_response": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["build"],
        "required_payload": ["query_id", "results"],
        "optional_payload": ["feature_metrics", "user_behavior", "response_time_ms"],
        "frequency": "on_event",
        "sla_minutes": 2,
        "priority": "AUTO",
    },
    # Analytics → Finance: Revenue anomaly
    "revenue_anomaly": {
        "sender_roles": ["analytics"],
        "recipient_roles": ["finance"],
        "required_payload": ["anomaly_type", "detected_at"],
        "optional_payload": ["severity", "details"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Finance → Ops: Pricing response
    "pricing_response": {
        "sender_roles": ["finance"],
        "recipient_roles": ["ops"],
        "required_payload": ["query_id", "floor", "ceiling"],
        "optional_payload": ["notes", "valid_until"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Finance → Ops: Invoice ready
    "invoice_ready": {
        "sender_roles": ["finance"],
        "recipient_roles": ["ops"],
        "required_payload": ["invoice_id", "client_id", "amount"],
        "optional_payload": ["due_date", "items"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Finance → Ops: Payment overdue (fires IMMEDIATELY on detection)
    "payment_overdue": {
        "sender_roles": ["finance"],
        "recipient_roles": ["ops"],
        "required_payload": ["invoice_id", "client_id", "days_overdue"],
        "optional_payload": ["amount", "last_contact"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Ops → Build: Feature brief
    "feature_brief": {
        "sender_roles": ["ops"],
        "recipient_roles": ["build"],
        "required_payload": ["project_id", "feature_name", "description"],
        "optional_payload": ["priority", "deadline", "client_id"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Ops → Content/Build: Project brief (after pricing confirmed)
    "project_brief": {
        "sender_roles": ["ops"],
        "recipient_roles": ["content", "build"],
        "required_payload": ["project_id", "client_id", "scope", "deadline"],
        "optional_payload": [
            "tone_requirements",
            "platform_targets",
            "budget",
            "brief_text",
        ],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Finance → Analytics: Revenue summary (totals only — no line items)
    "revenue_summary": {
        "sender_roles": ["finance"],
        "recipient_roles": ["analytics"],
        "required_payload": ["week_total", "invoices_paid", "invoices_pending"],
        "optional_payload": ["week_over_week_pct", "period_start", "period_end"],
        "frequency": "weekly",
        "priority": "AUTO",
    },
    # Ops → Finance: Project complete
    "project_complete": {
        "sender_roles": ["ops"],
        "recipient_roles": ["finance"],
        "required_payload": ["project_id", "client_id"],
        "optional_payload": ["completed_at", "final_amount"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Ops → Finance: Pricing query
    "pricing_query": {
        "sender_roles": ["ops"],
        "recipient_roles": ["finance"],
        "required_payload": [
            "project_id",
            "scope_description",
            "complexity_estimate",
            "deadline",
        ],
        "optional_payload": ["client_id", "urgency"],
        "frequency": "on_event",
        "sla_minutes": 10,
        "priority": "AUTO",
    },
    # Ops → Analytics: Client onboarded
    "client_onboarded": {
        "sender_roles": ["ops"],
        "recipient_roles": ["analytics"],
        "required_payload": [
            "client_id",
            "niche",
            "project_type",
            "estimated_value",
        ],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Build → Analytics: Behavior query
    "behavior_query": {
        "sender_roles": ["build"],
        "recipient_roles": ["analytics"],
        "required_payload": ["query"],
        "optional_payload": ["feature_id", "time_range"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
    # Build → Ops: Feature brief acknowledgment (within 10 min of receipt)
    "feature_brief_acknowledged": {
        "sender_roles": ["build"],
        "recipient_roles": ["ops"],
        "required_payload": [
            "project_id",
            "estimated_start",
            "clarity_score",
        ],
        "optional_payload": ["missing_elements", "deadline_risk"],
        "frequency": "on_event",
        "sla_minutes": 10,
        "priority": "AUTO",
    },
    # Finance → War Room: Overdue payment alert
    "overdue_alert": {
        "sender_roles": ["finance"],
        "recipient_roles": ["war_room"],
        "required_payload": ["invoice_id", "client_id", "amount", "days_overdue"],
        "optional_payload": ["last_contact", "escalation_level"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Assistant → Any Claw: Query (read-only status request)
    "assistant_query": {
        "sender_roles": ["assistant"],
        "recipient_roles": [
            "content",
            "ops",
            "analytics",
            "finance",
            "build",
            "assistant",
        ],
        "required_payload": ["query"],
        "optional_payload": ["context", "priority_hint"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Assistant → Any Claw: Task assignment (requires operator approval)
    "assistant_task": {
        "sender_roles": ["assistant"],
        "recipient_roles": [
            "content",
            "ops",
            "analytics",
            "finance",
            "build",
            "assistant",
        ],
        "required_payload": ["task_description", "deadline"],
        "optional_payload": ["context", "priority_hint", "attachments"],
        "frequency": "on_event",
        "priority": "REVIEW",
    },
    # Claw → Assistant: Response to assistant query
    "assistant_response": {
        "sender_roles": [
            "content",
            "ops",
            "analytics",
            "finance",
            "build",
            "assistant",
        ],
        "required_payload": ["query_id", "response"],
        "optional_payload": ["data", "confidence", "generated_at"],
        "frequency": "on_event",
        "priority": "AUTO",
    },
}


# ---------------------------------------------------------------------------
# Payload Schema Validation
# ---------------------------------------------------------------------------


def _validate_payload_schema(message: ClawMessage) -> ValidationResult:
    """
    Validate message payload against MESSAGE_TYPE_SCHEMAS.

    Checks:
    1. All required_payload fields are present
    2. Sender/recipient roles match schema requirements (if defined)
    """
    schema = MESSAGE_TYPE_SCHEMAS.get(message.message_type)
    if not schema:
        return ValidationResult(
            valid=True,
            reason=f"No schema defined for message type '{message.message_type}'",
            message_id=message.message_id,
        )

    if "sender_roles" in schema:
        if message.sender_role not in schema["sender_roles"]:
            return ValidationResult(
                valid=False,
                reason=(
                    f"Invalid sender for '{message.message_type}': "
                    f"expected one of {schema['sender_roles']}, "
                    f"got '{message.sender_role}'"
                ),
                message_id=message.message_id,
            )

    if "recipient_roles" in schema:
        if message.recipient_role not in schema["recipient_roles"]:
            return ValidationResult(
                valid=False,
                reason=(
                    f"Invalid recipient for '{message.message_type}': "
                    f"expected one of {schema['recipient_roles']}, "
                    f"got '{message.recipient_role}'"
                ),
                message_id=message.message_id,
            )

    required_fields = schema.get("required_payload", [])
    missing = [f for f in required_fields if f not in message.payload]
    if missing:
        return ValidationResult(
            valid=False,
            reason=(
                f"Missing required payload fields for '{message.message_type}': "
                f"{', '.join(missing)}"
            ),
            message_id=message.message_id,
        )

    return ValidationResult(
        valid=True,
        reason="Payload passes schema validation",
        message_id=message.message_id,
    )


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ClawMessage:
    """A typed message between claws in the squad mesh."""

    sender_role: str
    recipient_role: str
    message_type: str
    payload: dict[str, Any]
    squad_id: str
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class ValidationResult:
    """Result of a message contract validation."""

    valid: bool
    reason: str
    message_id: str = ""


@dataclass(frozen=True)
class MessageTypeConfig:
    """Configuration for a message type from mesh_config."""

    description: str
    requires_approval: bool = False


# ---------------------------------------------------------------------------
# Contract Validator
# ---------------------------------------------------------------------------


class ContractValidator:
    """
    Validates inter-claw messages against the squad's mesh configuration.

    Checks:
    1. Sender and recipient roles are valid
    2. Message type is valid
    3. The sender→recipient→message_type route is allowed by the matrix
    """

    def __init__(
        self,
        message_matrix: dict[str, dict[str, list[str]]],
        message_types: dict[str, MessageTypeConfig],
    ) -> None:
        self._matrix = message_matrix
        self._types = message_types

    @classmethod
    def from_config_file(cls, path: str | Path) -> ContractValidator:
        """Load a contract validator from a mesh config YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Mesh config not found: {config_path}")

        with config_path.open() as f:
            raw: dict[str, Any] = yaml.safe_load(f)

        return cls._from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ContractValidator:
        """Create a contract validator from a parsed config dictionary."""
        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> ContractValidator:
        matrix = raw.get("message_matrix", {})

        types_raw = raw.get("message_types", {})
        types: dict[str, MessageTypeConfig] = {}
        for name, config in types_raw.items():
            types[name] = MessageTypeConfig(
                description=config.get("description", ""),
                requires_approval=config.get("requires_approval", False),
            )

        return cls(message_matrix=matrix, message_types=types)

    def validate(self, message: ClawMessage) -> ValidationResult:
        """
        Validate a message against the contract rules.

        Returns ValidationResult with valid=True if the message passes
        all checks, or valid=False with a reason explaining the rejection.
        """
        # 1. Validate sender role
        if message.sender_role not in VALID_SENDERS:
            return ValidationResult(
                valid=False,
                reason=f"Invalid sender role: '{message.sender_role}'. Must be one of: {', '.join(sorted(VALID_SENDERS))}",
                message_id=message.message_id,
            )

        # 2. Validate recipient role
        if message.recipient_role not in VALID_RECIPIENTS:
            return ValidationResult(
                valid=False,
                reason=f"Invalid recipient role: '{message.recipient_role}'. Must be one of: {', '.join(sorted(VALID_RECIPIENTS))}",
                message_id=message.message_id,
            )

        # 3. Validate message type
        if message.message_type not in VALID_MESSAGE_TYPES:
            return ValidationResult(
                valid=False,
                reason=f"Invalid message type: '{message.message_type}'. Must be one of: {', '.join(sorted(VALID_MESSAGE_TYPES))}",
                message_id=message.message_id,
            )

        # 4. Check message matrix authorization
        sender_routes = self._matrix.get(message.sender_role, {})
        allowed_types = sender_routes.get(message.recipient_role, [])

        if message.message_type not in allowed_types:
            return ValidationResult(
                valid=False,
                reason=(
                    f"Unauthorized: {message.sender_role} cannot send "
                    f"'{message.message_type}' to {message.recipient_role}. "
                    f"Allowed types: {allowed_types or 'none'}"
                ),
                message_id=message.message_id,
            )

        # 5. Validate payload against schema if defined
        schema_result = _validate_payload_schema(message)
        if not schema_result.valid:
            return schema_result

        return ValidationResult(
            valid=True,
            reason="Message passes all contract checks",
            message_id=message.message_id,
        )

    def requires_approval(self, message_type: str) -> bool:
        """Check if a message type requires War Room approval."""
        type_config = self._types.get(message_type)
        return type_config.requires_approval if type_config else False

    def get_allowed_types(self, sender: str, recipient: str) -> list[str]:
        """Get the list of message types allowed from sender to recipient."""
        return self._matrix.get(sender, {}).get(recipient, [])

    def get_all_senders_for(self, recipient: str) -> dict[str, list[str]]:
        """Get all roles that can send messages to a given recipient."""
        result: dict[str, list[str]] = {}
        for sender, routes in self._matrix.items():
            types = routes.get(recipient, [])
            if types:
                result[sender] = types
        return result
