#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Content Approval Handler.

Tests cover:
- Approve: file move, logging, scheduling
- Edit: minor edit auto-approve, major edit re-queue
- Block: rejection handling, alert threshold
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from orchestrator.content.content_init import (
    ContentFilesystemInit,
    ContentOperationalLog,
)
from orchestrator.content.content_generator import Draft
from orchestrator.content.approval_handler import (
    ContentApprovalHandler,
    ApprovalResult,
    EditDelta,
    RejectionAlert,
    REQUEUE_THRESHOLD,
    REJECTION_ALERT_THRESHOLD,
)


class TestEditDelta:
    """Tests for edit delta calculation."""

    def test_no_change_zero_delta(self):
        """Identical content has zero delta."""
        handler = ContentApprovalHandler(MagicMock(), MagicMock())

        content = "This is the original content"
        delta = handler._calculate_edit_delta(content, content)

        assert delta.change_ratio == 0.0
        assert delta.significant is False
        assert delta.original_length == delta.edited_length

    def test_minor_change_below_threshold(self):
        """Minor change below 20% threshold."""
        handler = ContentApprovalHandler(MagicMock(), MagicMock())

        original = "This is the original content that is reasonably long"
        edited = "This is the original content that is reasonably good"

        delta = handler._calculate_edit_delta(original, edited)

        assert delta.change_ratio < REQUEUE_THRESHOLD
        assert delta.significant is False

    def test_major_change_above_threshold(self):
        """Major change above 20% threshold."""
        handler = ContentApprovalHandler(MagicMock(), MagicMock())

        original = "This is the original content for our campaign"
        edited = "Completely different message for brand new audience"

        delta = handler._calculate_edit_delta(original, edited)

        assert delta.change_ratio > REQUEUE_THRESHOLD
        assert delta.significant is True

    def test_empty_original(self):
        """Empty original calculates correctly."""
        handler = ContentApprovalHandler(MagicMock(), MagicMock())

        delta = handler._calculate_edit_delta("", "New content")

        assert delta.change_ratio == 1.0
        assert delta.original_length == 0
        assert delta.significant is True

    def test_empty_edited(self):
        """Empty edited calculates correctly."""
        handler = ContentApprovalHandler(MagicMock(), MagicMock())

        delta = handler._calculate_edit_delta("Original content", "")

        assert delta.change_ratio == 1.0
        assert delta.significant is True


class TestHandleApprove:
    """Tests for handle_approve method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with draft."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        handler = ContentApprovalHandler(fs, op_log)

        draft = Draft(
            draft_id="draft-test123",
            platform="twitter",
            client_id="client-1",
            project_id="proj-1",
            content_type="post",
            raw_content="raw",
            processed_content="Test content for approval",
        )

        pending_path = fs.get_draft_path("pending", draft.draft_id)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(draft.to_dict()))

        return fs, op_log, handler, draft

    def test_approve_moves_to_approved(self, tmp_path: Path):
        """Approved draft is moved to approved directory."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        result = handler.handle_approve(draft.draft_id, "action-123")

        assert result.success is True
        assert result.action == "approve"

        approved_path = fs.get_draft_path("approved", draft.draft_id)
        assert approved_path.exists()

        pending_path = fs.get_draft_path("pending", draft.draft_id)
        assert not pending_path.exists()

    def test_approve_logs_to_operational(self, tmp_path: Path):
        """Approval creates operational log entry."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        handler.handle_approve(draft.draft_id, "action-456")

        entries = op_log.read_recent(days=1, action_type="draft_approved")
        assert len(entries) == 1

        entry = entries[0]
        assert entry.entity_id == draft.draft_id
        assert entry.outcome == "success"

    def test_approve_logs_to_approvals_log(self, tmp_path: Path):
        """Approval creates approvals.log entry."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        handler.handle_approve(draft.draft_id, "action-789")

        approvals_path = fs.BASE / "logs" / "approvals.log"
        assert approvals_path.exists()

        lines = approvals_path.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["draft_id"] == draft.draft_id
        assert entry["decision"] == "APPROVED"

    def test_approve_scheduled_draft(self, tmp_path: Path):
        """Scheduled draft writes to calendar."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        draft.scheduled_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        pending_path = fs.get_draft_path("pending", draft.draft_id)
        pending_path.write_text(json.dumps(draft.to_dict()))

        handler.handle_approve(draft.draft_id, "action-sched")

        calendar_path = fs.BASE / "calendar" / "scheduled" / f"{draft.draft_id}.json"
        assert calendar_path.exists()

    def test_approve_missing_draft_returns_error(self, tmp_path: Path):
        """Missing draft returns error result."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        result = handler.handle_approve("nonexistent-draft", "action-x")

        assert result.success is False
        assert "not found" in result.message.lower()


class TestHandleEdit:
    """Tests for handle_edit method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with draft."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        handler = ContentApprovalHandler(fs, op_log)

        draft = Draft(
            draft_id="draft-edit-test",
            platform="linkedin",
            client_id="client-2",
            project_id="proj-2",
            content_type="article",
            raw_content="raw",
            processed_content="This is the original content that needs some editing work done.",
        )

        pending_path = fs.get_draft_path("pending", draft.draft_id)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(draft.to_dict()))

        return fs, op_log, handler, draft

    def test_minor_edit_auto_approves(self, tmp_path: Path):
        """Minor edit below threshold auto-approves."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        minor_edit = "This is the original content that needs some editing work completed."

        result = handler.handle_edit(draft.draft_id, minor_edit, "action-edit1")

        assert result.success is True
        assert result.requeued is False

        approved_path = fs.get_draft_path("approved", draft.draft_id)
        assert approved_path.exists()

    def test_major_edit_requeues(self, tmp_path: Path):
        """Major edit above threshold re-queues."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        major_edit = "Completely different content with a brand new message for the target audience."

        result = handler.handle_edit(draft.draft_id, major_edit, "action-edit2")

        assert result.success is True
        assert result.requeued is True
        assert result.new_draft_id is not None

        new_pending_path = fs.get_draft_path("pending", result.new_draft_id)
        assert new_pending_path.exists()

    def test_edit_saves_original(self, tmp_path: Path):
        """Edit preserves original draft."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        major_edit = "Completely rewritten content here."

        handler.handle_edit(draft.draft_id, major_edit, "action-edit3")

        original_path = fs.BASE / "drafts" / "pending" / f"{draft.draft_id}_original.json"
        assert original_path.exists()

    def test_edit_logs_to_operational(self, tmp_path: Path):
        """Edit creates operational log entry."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        minor_edit = "Small change to the content."

        handler.handle_edit(draft.draft_id, minor_edit, "action-edit4")

        entries = op_log.read_recent(days=1, action_type="draft_edited")
        assert len(entries) == 1

        entry = entries[0]
        assert "change_ratio" in entry.details


class TestHandleBlock:
    """Tests for handle_block method."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment with draft."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        handler = ContentApprovalHandler(fs, op_log)

        draft = Draft(
            draft_id="draft-block-test",
            platform="instagram",
            client_id="client-3",
            project_id="proj-3",
            content_type="story",
            raw_content="raw",
            processed_content="Content to be rejected",
        )

        pending_path = fs.get_draft_path("pending", draft.draft_id)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(draft.to_dict()))

        return fs, op_log, handler, draft

    def test_block_moves_to_rejected(self, tmp_path: Path):
        """Blocked draft is moved to rejected directory."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        result = handler.handle_block(draft.draft_id, "action-block1", "Not on brand")

        assert result.success is True
        assert result.action == "block"

        rejected_path = fs.get_draft_path("rejected", draft.draft_id)
        assert rejected_path.exists()

        pending_path = fs.get_draft_path("pending", draft.draft_id)
        assert not pending_path.exists()

    def test_block_logs_with_reason(self, tmp_path: Path):
        """Block logs reason to approvals log."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        handler.handle_block(draft.draft_id, "action-block2", "Tone mismatch")

        approvals_path = fs.BASE / "logs" / "approvals.log"
        entry = json.loads(approvals_path.read_text().strip())

        assert entry["decision"] == "BLOCKED"
        assert entry["reason"] == "Tone mismatch"

    def test_block_logs_to_operational(self, tmp_path: Path):
        """Block creates operational log entry."""
        fs, op_log, handler, draft = self._create_test_env(tmp_path)

        handler.handle_block(draft.draft_id, "action-block3", "Quality issues")

        entries = op_log.read_recent(days=1, action_type="draft_rejected")
        assert len(entries) == 1


class TestRejectionAlert:
    """Tests for rejection alert threshold."""

    def _create_test_env(self, tmp_path: Path):
        """Create test environment."""
        fs = ContentFilesystemInit(base_path=tmp_path)
        fs.initialize()

        log_path = tmp_path / "logs" / "operational.log"
        op_log = ContentOperationalLog(log_path)

        handler = ContentApprovalHandler(fs, op_log)

        return fs, op_log, handler

    def test_third_rejection_triggers_alert(self, tmp_path: Path):
        """Third rejection on same brief triggers alert."""
        fs, op_log, handler = self._create_test_env(tmp_path)

        project_id = "proj-alert-test"
        rejected_dir = fs.BASE / "drafts" / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)

        for i in range(REJECTION_ALERT_THRESHOLD):
            draft = Draft(
                draft_id=f"draft-rejected-{i}",
                platform="twitter",
                client_id="client-x",
                project_id=project_id,
                content_type="post",
                raw_content="raw",
                processed_content="content",
                status="rejected",
            )
            (rejected_dir / f"draft-rejected-{i}.json").write_text(json.dumps(draft.to_dict()))

        pending_draft = Draft(
            draft_id="draft-final-reject",
            platform="twitter",
            client_id="client-x",
            project_id=project_id,
            content_type="post",
            raw_content="raw",
            processed_content="final content",
        )
        pending_path = fs.get_draft_path("pending", pending_draft.draft_id)
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        pending_path.write_text(json.dumps(pending_draft.to_dict()))

        alert = handler._check_rejection_alert(pending_draft)

        assert alert is not None
        assert alert.brief_id == project_id
        assert alert.rejection_count >= REJECTION_ALERT_THRESHOLD

    def test_below_threshold_no_alert(self, tmp_path: Path):
        """Below threshold does not trigger alert."""
        fs, op_log, handler = self._create_test_env(tmp_path)

        draft = Draft(
            draft_id="draft-no-alert",
            platform="twitter",
            client_id="client-y",
            project_id="proj-no-alert",
            content_type="post",
            raw_content="raw",
            processed_content="content",
        )

        alert = handler._check_rejection_alert(draft)

        assert alert is None
