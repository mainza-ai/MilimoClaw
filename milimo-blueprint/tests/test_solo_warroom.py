#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_warroom.py - War Room Queue
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orchestrator.solo_warroom import (
    SoloWarRoom,
    WarRoomAction,
    ActionPriority,
    ActionStatus,
)


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "war_room": {
        "operator": "mainza",
        "mode": "solo",
        "queue_priority": {
            "1": "HOLD",
            "2": "REVIEW",
            "3": "AUTO",
        },
        "digest_schedule": {
            "morning_brief": "07:00",
            "evening_wrap": "20:00",
        },
    },
    "operator_policy": {
        "approval_modes": {
            "content": {
                "social_post_draft": "AUTO",
                "client_proposal_draft": "REVIEW",
            },
            "ops": {
                "new_client_inquiry": "REVIEW",
                "scope_change": "HOLD",
            },
            "finance": {
                "invoice_generation": "REVIEW",
                "invoice_send": "HOLD",
            },
            "analytics": {
                "weekly_report": "AUTO",
            },
            "build": {
                "pr_open": "REVIEW",
                "pr_merge": "HOLD",
            },
        },
    },
}


# ---------------------------------------------------------------------------

class TestSoloWarRoom:
    """Tests for SoloWarRoom class."""

    @pytest.fixture
    def warroom(self, tmp_path: Path) -> SoloWarRoom:
        """Create a War Room instance for testing."""
        return SoloWarRoom(VALID_CONFIG, log_dir=tmp_path)

    def test_initialization(self, warroom: SoloWarRoom) -> None:
        """Test War Room initialization."""
        assert warroom.operator == "mainza"
        assert warroom.mode == "solo"
        assert warroom.log_file.exists()

    def test_queue_action_review(self, warroom: SoloWarRoom) -> None:
        """Test queuing an action with REVIEW priority."""
        action = warroom.queue_action(
            claw="content",
            action_type="client_proposal_draft",
            payload={"title": "Test Proposal"},
        )

        assert action.priority == ActionPriority.REVIEW
        assert action.status == ActionStatus.PENDING
        assert action.claw == "content"

    def test_queue_action_hold(self, warroom: SoloWarRoom) -> None:
        """Test queuing an action with HOLD priority."""
        action = warroom.queue_action(
            claw="finance",
            action_type="invoice_send",
            payload={"amount": 1000},
        )

        assert action.priority == ActionPriority.HOLD
        assert action.status == ActionStatus.PENDING

    def test_queue_action_auto(self, warroom: SoloWarRoom) -> None:
        """Test queuing an action with AUTO priority."""
        action = warroom.queue_action(
            claw="content",
            action_type="social_post_draft",
            payload={"content": "Test post"},
        )

        assert action.priority == ActionPriority.AUTO
        assert action.status == ActionStatus.AUTO_EXECUTED

    def test_get_pending_all(self, warroom: SoloWarRoom) -> None:
        """Test getting all pending actions."""
        warroom.queue_action("content", "client_proposal_draft", {})
        warroom.queue_action("ops", "new_client_inquiry", {})

        pending = warroom.get_pending()

        assert len(pending) == 2

    def test_get_pending_by_priority(self, warroom: SoloWarRoom) -> None:
        """Test getting pending actions filtered by priority."""
        warroom.queue_action("finance", "invoice_send", {})  # HOLD
        warroom.queue_action("content", "client_proposal_draft", {})  # REVIEW
        warroom.queue_action("content", "social_post_draft", {"content": "test"})  # AUTO

        hold_pending = warroom.get_pending(priority_filter=ActionPriority.HOLD)
        review_pending = warroom.get_pending(priority_filter=ActionPriority.REVIEW)

        assert len(hold_pending) == 1
        assert len(review_pending) == 1

    def test_approve_action(self, warroom: SoloWarRoom) -> None:
        """Test approving an action."""
        action = warroom.queue_action(
            claw="content",
            action_type="client_proposal_draft",
            payload={"title": "Test"},
        )

        approved = warroom.approve(action.id)

        assert approved is not None
        assert approved.status == ActionStatus.APPROVED
        assert approved.operator_decision == "approved"
        assert approved.decided_at is not None

    def test_approve_nonexistent_action(self, warroom: SoloWarRoom) -> None:
        """Test approving a non-existent action."""
        result = warroom.approve("nonexistent_id")

        assert result is None

    def test_block_action(self, warroom: SoloWarRoom) -> None:
        """Test blocking an action."""
        action = warroom.queue_action(
            claw="finance",
            action_type="invoice_send",
            payload={"amount": 5000},
        )

        blocked = warroom.block(action.id, reason="Too high")

        assert blocked is not None
        assert blocked.status == ActionStatus.BLOCKED
        assert blocked.operator_decision is not None
        assert "Too high" in blocked.operator_decision

    def test_block_action_without_reason(self, warroom: SoloWarRoom) -> None:
        """Test blocking an action without a reason."""
        action = warroom.queue_action(
            claw="build",
            action_type="pr_merge",
            payload={"pr_number": 123},
        )

        blocked = warroom.block(action.id)

        assert blocked is not None
        assert blocked.status == ActionStatus.BLOCKED
        assert blocked.operator_decision == "blocked"

    def test_auto_execute_action(self, warroom: SoloWarRoom) -> None:
        """Test auto-executing an action."""
        action = warroom.queue_action(
            claw="content",
            action_type="client_proposal_draft",
            payload={},
        )

        executed = warroom.auto_execute(action.id)

        assert executed is not None
        assert executed.status == ActionStatus.AUTO_EXECUTED
        assert executed.operator_decision == "auto_executed"

    def test_priority_ordering(self, warroom: SoloWarRoom) -> None:
        """Test that queue is sorted by priority (HOLD first)."""
        warroom.queue_action("content", "client_proposal_draft", {})  # REVIEW
        warroom.queue_action("finance", "invoice_send", {})  # HOLD
        warroom.queue_action("ops", "new_client_inquiry", {})  # REVIEW

        pending = warroom.get_pending()

        assert pending[0].priority == ActionPriority.HOLD
        assert pending[1].priority == ActionPriority.REVIEW
        assert pending[2].priority == ActionPriority.REVIEW

    def test_get_stats(self, warroom: SoloWarRoom) -> None:
        """Test getting queue statistics."""
        warroom.queue_action("finance", "invoice_send", {})  # HOLD
        warroom.queue_action("content", "client_proposal_draft", {})  # REVIEW
        warroom.queue_action("content", "social_post_draft", {"test": "test"})  # AUTO

        stats = warroom.get_stats()

        assert stats["total_pending"] == 2  # AUTO is auto-executed
        assert stats["hold_count"] == 1
        assert stats["review_count"] == 1
        assert stats["auto_executed_today"] == 1

    def test_logging(self, warroom: SoloWarRoom, tmp_path: Path) -> None:
        """Test that actions are logged."""
        action = warroom.queue_action(
            claw="content",
            action_type="client_proposal_draft",
            payload={},
        )
        warroom.approve(action.id)

        assert warroom.log_file.exists() or len(warroom._processed) > 0

    def test_print_morning_brief(self, warroom: SoloWarRoom, capsys) -> None:
        """Test printing morning brief."""
        warroom.queue_action("content", "client_proposal_draft", {})
        warroom.print_morning_brief()

        captured = capsys.readouterr()
        assert "MORNING BRIEF" in captured.out
        assert "Queue Status" in captured.out

    def test_print_evening_wrap(self, warroom: SoloWarRoom, capsys) -> None:
        """Test printing evening wrap."""
        warroom.queue_action("content", "client_proposal_draft", {})
        warroom.approve(warroom.get_pending()[0].id)
        warroom.print_evening_wrap()

        captured = capsys.readouterr()
        assert "EVENING WRAP" in captured.out
        assert "Today's Summary" in captured.out

    def test_export_log(self, warroom: SoloWarRoom, tmp_path: Path) -> None:
        """Test exporting log to file."""
        action = warroom.queue_action(
            claw="content",
            action_type="client_proposal_draft",
            payload={"title": "Test"},
        )
        warroom.approve(action.id)

        export_path = tmp_path / "export.json"
        warroom.export_log(export_path)

        assert export_path.exists()

        with export_path.open("r") as f:
            data = json.load(f)

        assert data["operator"] == "mainza"
        assert len(data["processed"]) == 1

    def test_auto_actions_not_in_pending(self, warroom: SoloWarRoom) -> None:
        """Test that AUTO actions are auto-executed and not in pending."""
        warroom.queue_action("content", "social_post_draft", {"content": "test"})

        pending = warroom.get_pending()

        assert len(pending) == 0

    def test_unknown_action_type_defaults_to_review(self, warroom: SoloWarRoom) -> None:
        """Test that unknown action types default to REVIEW."""
        action = warroom.queue_action(
            claw="content",
            action_type="unknown_action_type",
            payload={},
        )

        assert action.priority == ActionPriority.REVIEW

    def test_multiple_actions_same_claw(self, warroom: SoloWarRoom) -> None:
        """Test queuing multiple actions from same claw."""
        warroom.queue_action("finance", "invoice_generation", {})  # REVIEW
        warroom.queue_action("finance", "invoice_send", {})  # HOLD
        warroom.queue_action("finance", "expense_log", {})  # Unknown, REVIEW

        pending = warroom.get_pending()

        assert len(pending) == 3
        assert pending[0].priority == ActionPriority.HOLD


class TestWarRoomAction:
    """Tests for WarRoomAction dataclass."""

    def test_action_id_generated(self) -> None:
        """Test that action ID is auto-generated."""
        action = WarRoomAction(claw="content", action_type="test")
        assert action.id.startswith("act_")

    def test_action_has_timestamp(self) -> None:
        """Test that action has created_at timestamp."""
        action = WarRoomAction(claw="content", action_type="test")
        assert action.created_at is not None
        assert isinstance(action.created_at, datetime)


class TestActionPriority:
    """Tests for ActionPriority enum."""

    def test_hold_highest_priority(self) -> None:
        """Test that HOLD has highest priority (lowest number)."""
        assert ActionPriority.HOLD.value < ActionPriority.REVIEW.value
        assert ActionPriority.REVIEW.value < ActionPriority.AUTO.value

    def test_priority_values(self) -> None:
        """Test priority values."""
        assert ActionPriority.HOLD.value == 1
        assert ActionPriority.REVIEW.value == 2
        assert ActionPriority.AUTO.value == 3


class TestActionStatus:
    """Tests for ActionStatus enum."""

    def test_status_values(self) -> None:
        """Test status values."""
        assert ActionStatus.PENDING.value == "pending"
        assert ActionStatus.APPROVED.value == "approved"
        assert ActionStatus.BLOCKED.value == "blocked"
        assert ActionStatus.AUTO_EXECUTED.value == "auto_executed"
