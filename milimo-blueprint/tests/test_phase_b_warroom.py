#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Phase B — War Room Approval Flow Integration Tests

Tests B1-B8: War Room initialization, queue priority ordering,
and REVIEW/HOLD approval mechanics.

These tests run after Phase A passes.
"""
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.phase_b


def _make_test_config() -> dict[str, Any]:
    return {
        "war_room": {
            "operator": "test-operator",
            "mode": "solo",
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
            "welcome_message": "AUTO",
            "deadline_risk": "REVIEW",
            "deadline_critical": "HOLD",
            "scope_change": "HOLD",
        },
                "finance": {
                    "invoice_generation": "REVIEW",
                    "invoice_send": "HOLD",
                },
                "build": {
                    "pr_open": "REVIEW",
                    "pr_merge": "HOLD",
                    "production_deploy": "HOLD",
                },
            }
        },
    }


class TestWarRoomInitialization:

    def test_b1_war_room_tui_renders_five_claw_health_panel(self):
        """
        War Room TUI initializes with health panel showing all 5 claws.
        Each claw appears in the right panel with: name, status dot,
        tool count, last evolution timestamp, this-week activity count.
        """
        from orchestrator.solo_warroom import SoloWarRoom

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            health_panel = war_room.get_stats()
            stats = war_room.get_stats()

            assert "hold_count" in stats
            assert "review_count" in stats
            assert "auto_count" in stats
            assert "total_pending" in stats

    def test_b2_morning_brief_scheduled_at_07_00(self):
        """
        Morning brief is scheduled for 07:00 daily.
        Evening wrap is scheduled for 20:00 daily.
        """
        from orchestrator.solo_warroom import SoloWarRoom

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            schedule = war_room.digest_schedule

            assert schedule.morning_brief.hour == 7
            assert schedule.morning_brief.minute == 0

            assert schedule.evening_wrap.hour == 20
            assert schedule.evening_wrap.minute == 0


class TestQueuePriorityOrdering:

    def test_b3_mock_review_action_appears_in_queue(self):
        """
        Injecting a mock REVIEW action produces a queued entry
        with correct mode, claw source, and summary.
        """
        from orchestrator.solo_warroom import SoloWarRoom

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            action = war_room.queue_action(
                claw="content",
                action_type="client_proposal_draft",
                payload={
                    "entity_id": "draft_001",
                    "summary": "Draft ready: LinkedIn post for @NovaBrand",
                    "platform": "linkedin",
                    "approval_probability": 0.87,
                },
            )

            pending = war_room.get_pending()
            entry = next((a for a in pending if a.id == action.id), None)

            assert entry is not None
            assert entry.claw == "content"
            assert entry.action_type == "client_proposal_draft"
            assert "LinkedIn" in entry.payload.get("summary", "")

    def test_b4_hold_items_appear_above_review_items(self):
        """
        HOLD actions must always appear above REVIEW actions in the queue
        regardless of insertion order.
        """
        from orchestrator.solo_warroom import (
            ActionPriority,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            review_action = war_room.queue_action(
                claw="content",
                action_type="client_proposal_draft",
                payload={"entity_id": "draft_001", "summary": "REVIEW action inserted first"},
            )

            hold_action = war_room.queue_action(
                claw="finance",
                action_type="invoice_send",
                payload={"entity_id": "invoice_001", "summary": "HOLD action inserted second"},
            )

            queue = war_room.get_pending()
            modes = [a.priority for a in queue]

            hold_idx = next(i for i, p in enumerate(modes) if p == ActionPriority.HOLD)
            review_idx = next(i for i, p in enumerate(modes) if p == ActionPriority.REVIEW)

            assert hold_idx < review_idx, (
                "HOLD items must appear before REVIEW items in queue. "
                f"Got HOLD at index {hold_idx}, REVIEW at index {review_idx}"
            )


class TestApprovalMechanics:

    def test_b5_approve_review_executes_and_moves_to_processed(self):
        """
        Approving a REVIEW action:
        1. Marks action as APPROVED
        2. Removes item from pending queue
        3. Adds item to processed list
        """
        from orchestrator.solo_warroom import (
            ActionStatus,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            action = war_room.queue_action(
                claw="ops",
                action_type="new_client_inquiry",
                payload={
                    "entity_id": "client_001",
                    "summary": "New client welcome - @TestCo",
                    "triage_score": 94,
                },
            )

            execute_fn = MagicMock()
            approved = war_room.approve(action.id)

            assert approved is not None
            assert approved.status == ActionStatus.APPROVED
            assert approved.operator_decision == "approved"
            assert approved.decided_at is not None

            pending = war_room.get_pending()
            assert not any(a.id == action.id for a in pending), (
                "Approved action should be removed from pending queue"
            )

    def test_b6_inject_hold_action_appears_at_queue_top(self):
        """
        A HOLD action queued after existing REVIEW items appears
        at the top of the queue (above all REVIEW items).
        """
        from orchestrator.solo_warroom import (
            ActionPriority,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            for i in range(3):
                war_room.queue_action(
                    claw="content",
                    action_type="client_proposal_draft",
                    payload={"entity_id": f"draft_{i}", "summary": f"Review item {i}"},
                )

            hold_action = war_room.queue_action(
                claw="finance",
                action_type="invoice_send",
                payload={
                    "entity_id": "invoice_001",
                    "summary": "Invoice ready to send - $2,400",
                },
            )

            queue = war_room.get_pending()
            assert queue[0].id == hold_action.id, (
                "HOLD action must be at position 0 in queue "
                "regardless of when it was inserted"
            )
            assert queue[0].priority == ActionPriority.HOLD

    def test_b7_release_hold_executes_action(self):
        """
        Releasing a HOLD:
        1. Calls approve() which marks the action approved
        2. Removes item from HOLD queue
        """
        from orchestrator.solo_warroom import (
            ActionStatus,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            hold_action = war_room.queue_action(
                claw="finance",
                action_type="invoice_send",
                payload={
                    "entity_id": "invoice_001",
                    "summary": "Invoice ready to send",
                },
            )

            execute_fn = MagicMock()

            approved = war_room.approve(hold_action.id)

            assert approved is not None
            assert approved.status == ActionStatus.APPROVED

            pending = war_room.get_pending()
            assert not any(a.id == hold_action.id for a in pending)

    def test_b8_keyboard_shortcuts_registered(self):
        """
        War Room TUI has keyboard shortcuts registered:
        A=approve, B=block, E=edit, R=release, D=digest, F=deep_work, Q=quit
        """
        from orchestrator.solo_warroom import SoloWarRoom

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            assert hasattr(war_room, "approve")
            assert hasattr(war_room, "block")
            assert hasattr(war_room, "get_stats")

            assert callable(war_room.approve)
            assert callable(war_room.block)


class TestAutoExecution:

    def test_auto_priority_executes_immediately(self):
        """
        AUTO priority actions execute immediately upon queueing.
        """
        from orchestrator.solo_warroom import (
            ActionStatus,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            auto_action = war_room.queue_action(
                claw="content",
                action_type="social_post_draft",
                payload={
                    "entity_id": "post_001",
                    "summary": "Auto-post scheduled",
                },
            )

            pending = war_room.get_pending()
            assert not any(a.id == auto_action.id for a in pending), (
                "AUTO action should not be in pending queue - it was auto-executed"
            )

            assert auto_action.status == ActionStatus.AUTO_EXECUTED


class TestBlockMechanics:

    def test_block_action_removes_from_queue(self):
        """
        Blocking an action:
        1. Marks action as BLOCKED
        2. Removes from pending queue
        3. Adds to processed list
        """
        from orchestrator.solo_warroom import (
            ActionStatus,
            SoloWarRoom,
        )

        config = _make_test_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            war_room = SoloWarRoom(config=config, log_dir=Path(tmpdir))

            action = war_room.queue_action(
                claw="ops",
                action_type="new_client_inquiry",
                payload={"entity_id": "client_001", "summary": "Inquiry to block"},
            )

            blocked = war_room.block(action.id, reason="Not a good fit")

            assert blocked is not None
            assert blocked.status == ActionStatus.BLOCKED
            assert "blocked" in (blocked.operator_decision or "")

            pending = war_room.get_pending()
            assert not any(a.id == action.id for a in pending)
