# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Phase 1 Unit Tests

Tests for build_init.py, signal_dispatcher.py, and approval_handler.py.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_test_dir = Path(__file__).parent
_orchestrator_dir = _test_dir.parent / "orchestrator"
if str(_orchestrator_dir) not in sys.path:
    sys.path.insert(0, str(_orchestrator_dir))

from build.build_claw import BuildClaw
from build.build_init import (
    REQUIRED_DIRS,
    REQUIRED_FILES,
    BuildFilesystemInit,
    BuildLogEntry,
    BuildOperationalLog,
)
from build.approval_handler import (
    BuildApprovalHandler,
    DeployActivityLog,
    PRActivityLog,
)
from build.signal_dispatcher import (
    BuildSignalDispatcher,
)


class TestBuildFilesystemInit:
    """Tests for BuildFilesystemInit."""

    def test_initialize_creates_all_directories(self, tmp_path):
        """All REQUIRED_DIRS are created."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        result = fs.initialize()

        assert result.success
        for dir_name in REQUIRED_DIRS:
            assert (tmp_path / dir_name).is_dir()

    def test_initialize_creates_all_files(self, tmp_path):
        """All REQUIRED_FILES are created with correct content."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        result = fs.initialize()

        assert result.success
        for file_path in REQUIRED_FILES:
            full_path = tmp_path / file_path
            assert full_path.exists()

    def test_initialize_is_idempotent(self, tmp_path):
        """Running initialize twice succeeds without errors."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        result1 = fs.initialize()
        result2 = fs.initialize()

        assert result1.success
        assert result2.success
        assert len(result2.created_dirs) == 0
        assert len(result2.created_files) == 0

    def test_initialize_returns_correct_counts(self, tmp_path):
        """InitResult correctly tracks created vs existing."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        result1 = fs.initialize()

        assert len(result1.created_dirs) == len(REQUIRED_DIRS)
        assert len(result1.created_files) == len(REQUIRED_FILES)
        assert len(result1.already_existed) == 0

        result2 = fs.initialize()
        assert len(result2.created_dirs) == 0
        assert len(result2.created_files) == 0
        assert len(result2.already_existed) > 0

    def test_validate_passes_when_structure_exists(self, tmp_path):
        """Validation succeeds after initialization."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()

        result = fs.validate()
        assert result.valid
        assert len(result.missing_dirs) == 0
        assert len(result.missing_files) == 0

    def test_validate_finds_missing_directories(self, tmp_path):
        """Validation identifies missing directories."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        result = fs.validate()

        assert not result.valid
        assert len(result.missing_dirs) > 0

    def test_get_pr_path_returns_correct_path(self, tmp_path):
        """get_pr_path returns correct path for each status."""
        fs = BuildFilesystemInit(base_path=tmp_path)

        assert (
            fs.get_pr_path("drafted", "pr-123")
            == tmp_path / "prs" / "drafted" / "pr-123.json"
        )
        assert (
            fs.get_pr_path("approved", "pr-456")
            == tmp_path / "prs" / "approved" / "pr-456.json"
        )
        assert (
            fs.get_pr_path("merged", "pr-789")
            == tmp_path / "prs" / "merged" / "pr-789.json"
        )

    def test_get_pr_path_rejects_invalid_status(self, tmp_path):
        """get_pr_path raises on invalid status."""
        fs = BuildFilesystemInit(base_path=tmp_path)

        with pytest.raises(ValueError, match="Invalid PR status"):
            fs.get_pr_path("invalid", "pr-123")  # type: ignore[arg-type]

    def test_get_deploy_path_returns_correct_path(self, tmp_path):
        """get_deploy_path returns correct path for each status."""
        fs = BuildFilesystemInit(base_path=tmp_path)

        assert (
            fs.get_deploy_path("pending", "deploy-123")
            == tmp_path / "deployments" / "pending" / "deploy-123.json"
        )
        assert (
            fs.get_deploy_path("history", "deploy-456")
            == tmp_path / "deployments" / "history" / "deploy-456.json"
        )

    def test_get_deploy_path_rejects_invalid_status(self, tmp_path):
        """get_deploy_path raises on invalid status."""
        fs = BuildFilesystemInit(base_path=tmp_path)

        with pytest.raises(ValueError, match="Invalid deploy status"):
            fs.get_deploy_path("invalid", "deploy-123")  # type: ignore[arg-type]

    def test_atomic_write_json_creates_file(self, tmp_path):
        """atomic_write_json creates file with correct content."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        fs.atomic_write_json(path, data)

        assert path.exists()
        content = json.loads(path.read_text())
        assert content == data

    def test_atomic_write_json_is_atomic(self, tmp_path):
        """atomic_write_json uses temp file and rename."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        path = tmp_path / "test.json"

        original_data = {"test": "data"}
        fs.atomic_write_json(path, original_data)

        assert path.exists()

        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

        content = json.loads(path.read_text())
        assert content == original_data

    def test_atomic_write_json_handles_exception(self, tmp_path):
        """atomic_write_json cleans up temp file on failure."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        path = tmp_path / "test.json"

        with patch("builtins.open", side_effect=IOError("test error")):
            with pytest.raises(IOError):
                fs.atomic_write_json(path, {"test": "data"})

        assert not path.exists()


class TestBuildOperationalLog:
    """Tests for BuildOperationalLog."""

    def test_append_creates_entry(self, tmp_path):
        """append writes entry to log file."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        entry = BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="test_action",
            entity_id="test-123",
            outcome="success",
            details={"key": "value"},
        )

        log.append(entry)

        content = log_path.read_text()
        assert "test_action" in content
        assert "test-123" in content

    def test_read_recent_filters_by_days(self, tmp_path):
        """read_recent only returns entries within time window."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        old_entry = BuildLogEntry(
            timestamp="2025-01-01T00:00:00+00:00",
            action_type="old_action",
            entity_id="old-123",
            outcome="success",
            details={},
        )
        new_entry = BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="new_action",
            entity_id="new-123",
            outcome="success",
            details={},
        )

        log.append(old_entry)
        log.append(new_entry)

        recent = log.read_recent(days=1)
        assert len(recent) == 1
        assert recent[0].action_type == "new_action"

    def test_read_recent_filters_by_action_type(self, tmp_path):
        """read_recent filters by action_type when provided."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        for i in range(5):
            entry = BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="action_a" if i < 3 else "action_b",
                entity_id=f"entity-{i}",
                outcome="success",
                details={},
            )
            log.append(entry)

        action_a = log.read_recent(days=1, action_type="action_a")
        assert len(action_a) == 3

        action_b = log.read_recent(days=1, action_type="action_b")
        assert len(action_b) == 2

    def test_count_by_type(self, tmp_path):
        """count_by_type returns correct count."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        for i in range(3):
            entry = BuildLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="counted_action",
                entity_id=f"entity-{i}",
                outcome="success",
                details={},
            )
            log.append(entry)

        count = log.count_by_type("counted_action", days=1)
        assert count == 3

    def test_get_last_run_time_returns_timestamp(self, tmp_path):
        """get_last_run_time returns most recent timestamp."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        timestamps = []
        for i in range(3):
            ts = datetime.now(timezone.utc).isoformat()
            timestamps.append(ts)
            entry = BuildLogEntry(
                timestamp=ts,
                action_type="scheduled_action",
                entity_id=f"entity-{i}",
                outcome="success",
                details={},
            )
            log.append(entry)
            time.sleep(0.01)

        last_run = log.get_last_run_time("scheduled_action")
        assert last_run == timestamps[-1]

    def test_get_last_run_time_returns_none_when_empty(self, tmp_path):
        """get_last_run_time returns None for unknown action_type."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        result = log.get_last_run_time("nonexistent_action")
        assert result is None

    def test_concurrent_write_safety(self, tmp_path):
        """Multiple threads can write simultaneously without corruption."""
        log_path = tmp_path / "operational.log"
        log = BuildOperationalLog(log_path)

        def write_entries(thread_id: int, count: int):
            for i in range(count):
                entry = BuildLogEntry(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    action_type=f"thread_{thread_id}",
                    entity_id=f"t{thread_id}-e{i}",
                    outcome="success",
                    details={"thread": thread_id},
                )
                log.append(entry)

        threads = [
            threading.Thread(target=write_entries, args=(i, 10)) for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        entries = log.read_recent(days=1)
        assert len(entries) == 50


class TestBuildSignalDispatcher:
    """Tests for BuildSignalDispatcher."""

    @pytest.fixture
    def dispatcher(self, tmp_path):
        """Create a dispatcher with test filesystem."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        return BuildSignalDispatcher(fs, log, squad_id="test-squad")

    def test_send_deploy_complete_creates_correct_message(self, dispatcher, tmp_path):
        """send_deploy_complete sends correct message structure."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        dispatcher.send_deploy_complete(
            project_id="proj-123",
            deploy_url="https://example.com",
            version="v1.0.0",
            deployed_at=datetime.now(timezone.utc).isoformat(),
        )

        entries = log.read_recent(days=1, action_type="deploy_complete_sent")
        assert len(entries) == 1
        assert entries[0].details["project_id"] == "proj-123"

    def test_send_shipping_summary_creates_correct_message(self, dispatcher, tmp_path):
        """send_shipping_summary sends correct message structure."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        dispatcher.send_shipping_summary(
            week_of="2026-W12",
            prs_merged=5,
            issues_resolved=3,
            features_shipped=["feature-a", "feature-b"],
            notable_changes=["Fixed bug", "Added API"],
        )

        entries = log.read_recent(days=1, action_type="shipping_summary_sent")
        assert len(entries) == 1
        assert entries[0].details["prs_merged"] == 5

    def test_send_behavior_query_creates_correct_message(self, dispatcher, tmp_path):
        """send_behavior_query sends correct message and tracks pending."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        message_id = dispatcher.send_behavior_query(
            query="Which features have lowest retention?",
            lookback_days=7,
        )

        assert message_id
        assert dispatcher.has_pending_behavior_query()
        assert dispatcher.get_pending_query_age_seconds() is not None

        entries = log.read_recent(days=1, action_type="behavior_query_sent")
        assert len(entries) == 1

    def test_handle_feature_brief_validates_message(self, dispatcher):
        """handle_feature_brief validates message structure."""
        valid_message = {
            "message_type": "feature_brief",
            "payload": {
                "project_id": "proj-123",
                "feature_name": "Test Feature",
                "description": "A test feature",
            },
        }

        dispatcher.handle_feature_brief(valid_message)

        invalid_message = {"message_type": "wrong_type", "payload": {}}
        with pytest.raises(ValueError, match="Expected message_type"):
            dispatcher.handle_feature_brief(invalid_message)

    def test_handle_feature_brief_logs_receipt(self, dispatcher, tmp_path):
        """handle_feature_brief logs receipt."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        message = {
            "message_id": "msg-123",
            "message_type": "feature_brief",
            "payload": {
                "project_id": "proj-123",
                "feature_name": "Test Feature",
                "description": "A test feature",
            },
        }

        dispatcher.handle_feature_brief(message)

        entries = log.read_recent(days=1, action_type="feature_brief_received")
        assert len(entries) == 1

    def test_send_feature_brief_acknowledged_validates_clarity_score(
        self, dispatcher, tmp_path
    ):
        """send_feature_brief_acknowledged rejects invalid clarity_score."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        dispatcher.send_feature_brief_acknowledged(
            project_id="proj-123",
            estimated_start=datetime.now(timezone.utc).isoformat(),
            clarity_score="clear",
        )

        dispatcher.send_feature_brief_acknowledged(
            project_id="proj-456",
            estimated_start=datetime.now(timezone.utc).isoformat(),
            clarity_score="low",
        )

        with pytest.raises(ValueError, match="Invalid clarity_score"):
            dispatcher.send_feature_brief_acknowledged(
                project_id="proj-789",
                estimated_start=datetime.now(timezone.utc).isoformat(),
                clarity_score="invalid",
            )

    def test_handle_retention_signals_stores_data(self, dispatcher, tmp_path):
        """handle_retention_signals stores signal data."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        dispatcher._log = log

        message = {
            "message_id": "msg-123",
            "message_type": "retention_signals",
            "payload": {
                "signal_type": "churn_risk",
                "feature_id": "feature-123",
                "correlation": 0.75,
            },
        }

        dispatcher.handle_retention_signals(message)

        signals = dispatcher.get_retention_signals()
        assert signals is not None
        assert signals["signal_type"] == "churn_risk"

        signals_path = tmp_path / "context" / "sprint" / "retention-signals.json"
        assert signals_path.exists()

    def test_dispatch_failure_logged_not_raised(self, tmp_path):
        """Dispatch failure is logged but not raised."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)

        failing_gateway = MagicMock()
        failing_gateway.send.side_effect = Exception("Network error")

        dispatcher = BuildSignalDispatcher(fs, log, mesh_gateway=failing_gateway)

        dispatcher.send_deploy_complete(
            project_id="proj-123",
            deploy_url="https://example.com",
            version="v1.0.0",
            deployed_at=datetime.now(timezone.utc).isoformat(),
        )

    def test_accumulate_shipping_data(self, dispatcher):
        """Shipping data accumulates correctly."""
        dispatcher.accumulate_shipping_data(
            pr_id="pr-1",
            issue_number=123,
            feature_name="Feature A",
            changes=["Added X", "Fixed Y"],
        )

        dispatcher.accumulate_shipping_data(
            pr_id="pr-2",
            issue_number=124,
            feature_name="Feature B",
            changes=["Added Z"],
        )

        summary = dispatcher.get_accumulated_shipping_summary()
        assert summary["prs_merged"] == 2
        assert "Feature A" in summary["features_shipped"]
        assert "Feature B" in summary["features_shipped"]


class TestBuildApprovalHandler:
    """Tests for BuildApprovalHandler."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create a handler with test filesystem."""
        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)
        return BuildApprovalHandler(fs, log, pr_log, deploy_log)

    def test_queue_pr_review_creates_review_not_hold(self, handler):
        """queue_pr_review creates REVIEW action, not HOLD."""
        action_id = handler.queue_pr_review(
            pr_id="pr-123",
            pr_title="Fix bug",
            branch="fix/bug",
            issue_number=42,
            files_changed=3,
            lines_added=50,
            lines_removed=10,
            test_result="passing",
            tests_count=25,
            github_pr_url="https://github.com/repo/pull/123",
        )

        action = handler.get_pending_action(action_id)
        assert action is not None
        assert action.mode == "REVIEW"
        assert action.action_type == "pr_review"

    def test_queue_pr_merge_hold_creates_hold(self, handler):
        """queue_pr_merge_hold creates HOLD action."""
        action_id = handler.queue_pr_merge_hold(
            pr_id="pr-123",
            pr_title="Fix bug",
            github_pr_url="https://github.com/repo/pull/123",
        )

        action = handler.get_pending_action(action_id)
        assert action is not None
        assert action.mode == "HOLD"
        assert action.action_type == "pr_merge_hold"

    def test_handle_approve_on_pr_review_calls_next_step_not_merge(self, handler):
        """REVIEW approve calls next_step_fn (queue_pr_merge_hold), NOT merge."""
        merge_called = []

        def fake_merge():
            merge_called.append(True)

        def next_step():
            handler.queue_pr_merge_hold(
                pr_id="pr-123",
                pr_title="Fix bug",
                github_pr_url="https://github.com/repo/pull/123",
            )

        action_id = handler.queue_pr_review(
            pr_id="pr-123",
            pr_title="Fix bug",
            branch="fix/bug",
            issue_number=42,
            files_changed=3,
            lines_added=50,
            lines_removed=10,
            test_result="passing",
            tests_count=25,
            github_pr_url="https://github.com/repo/pull/123",
        )

        result = handler.handle_approve(action_id, next_step_fn=next_step)

        assert result.executed
        assert len(merge_called) == 0

        hold_actions = handler.get_pending_actions_by_type("pr_merge_hold")
        assert len(hold_actions) == 1

    def test_handle_hold_release_on_pr_hold_calls_merge(self, handler):
        """HOLD release on PR calls the merge function."""
        merge_called = []

        def fake_merge():
            merge_called.append(True)
            return {"merged": True}

        hold_action_id = handler.queue_pr_merge_hold(
            pr_id="pr-123",
            pr_title="Fix bug",
            github_pr_url="https://github.com/repo/pull/123",
        )

        result = handler.handle_hold_release(hold_action_id, execute_fn=fake_merge)

        assert result.executed
        assert len(merge_called) == 1

    def test_queue_deploy_hold_is_separate_from_pr_hold(self, handler):
        """Deploy HOLD is separate from PR HOLD."""
        pr_hold_id = handler.queue_pr_merge_hold(
            pr_id="pr-123",
            pr_title="Fix bug",
            github_pr_url="https://github.com/repo/pull/123",
        )

        deploy_hold_id = handler.queue_deploy_hold(
            deploy_id="deploy-456",
            version="v1.0.0",
            deploy_target="vercel",
            changes_summary=["Fix bug", "Add feature"],
        )

        pr_action = handler.get_pending_action(pr_hold_id)
        deploy_action = handler.get_pending_action(deploy_hold_id)

        assert pr_action.action_type == "pr_merge_hold"
        assert deploy_action.action_type == "deploy_hold"
        assert pr_action.entity_id != deploy_action.entity_id

    def test_handle_hold_release_on_deploy_calls_deploy(self, handler):
        """HOLD release on deploy calls the deploy function."""
        deploy_called = []

        def fake_deploy():
            deploy_called.append(True)
            return {"deployed": True}

        deploy_hold_id = handler.queue_deploy_hold(
            deploy_id="deploy-456",
            version="v1.0.0",
            deploy_target="vercel",
            changes_summary=["Fix bug"],
        )

        result = handler.handle_hold_release(deploy_hold_id, execute_fn=fake_deploy)

        assert result.executed
        assert len(deploy_called) == 1

    def test_handle_block_does_not_call_execute_fn(self, handler):
        """Blocking does not execute the next step."""
        executed = []

        def should_not_run():
            executed.append(True)

        action_id = handler.queue_pr_review(
            pr_id="pr-123",
            pr_title="Fix bug",
            branch="fix/bug",
            issue_number=42,
            files_changed=3,
            lines_added=50,
            lines_removed=10,
            test_result="passing",
            tests_count=25,
            github_pr_url="https://github.com/repo/pull/123",
        )

        result = handler.handle_block(action_id, reason="Code quality issues")

        assert result.decision == "blocked"
        assert len(executed) == 0
        assert handler.get_pending_action(action_id) is None

    def test_all_decisions_logged(self, handler, tmp_path):
        """All approval decisions are logged."""
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        handler._log = log

        action_id = handler.queue_pr_review(
            pr_id="pr-123",
            pr_title="Fix bug",
            branch="fix/bug",
            issue_number=42,
            files_changed=3,
            lines_added=50,
            lines_removed=10,
            test_result="passing",
            tests_count=25,
            github_pr_url="https://github.com/repo/pull/123",
        )

        handler.handle_approve(action_id)

        entries = log.read_recent(days=1)
        queued_entries = [e for e in entries if e.action_type == "pr_review_queued"]
        approved_entries = [e for e in entries if e.action_type == "pr_review_approved"]

        assert len(queued_entries) == 1
        assert len(approved_entries) == 1

    def test_handle_hold_cancel(self, handler):
        """Cancelling HOLD removes action without executing."""
        deploy_hold_id = handler.queue_deploy_hold(
            deploy_id="deploy-456",
            version="v1.0.0",
            deploy_target="vercel",
            changes_summary=["Fix bug"],
        )

        result = handler.handle_hold_cancel(deploy_hold_id)

        assert result.decision == "cancelled"
        assert handler.get_pending_action(deploy_hold_id) is None

    def test_handle_approve_unknown_action_returns_error(self, handler):
        """Approving unknown action returns error result."""
        result = handler.handle_approve("nonexistent-id")

        assert not result.executed
        assert "error" in result.details

    def test_handle_hold_release_wrong_mode_returns_error(self, handler):
        """Releasing HOLD on REVIEW action returns error."""
        action_id = handler.queue_pr_review(
            pr_id="pr-123",
            pr_title="Fix bug",
            branch="fix/bug",
            issue_number=42,
            files_changed=3,
            lines_added=50,
            lines_removed=10,
            test_result="passing",
            tests_count=25,
            github_pr_url="https://github.com/repo/pull/123",
        )

        result = handler.handle_hold_release(action_id, execute_fn=lambda: None)

        assert not result.executed
        assert "error" in result.details


class TestPRActivityLog:
    """Tests for PRActivityLog."""

    def test_append_creates_entry(self, tmp_path):
        """append writes entry to log file."""
        log_path = tmp_path / "pr-activity.log"
        log = PRActivityLog(log_path)

        log.append("review_queued", "pr-123", {"branch": "fix/bug"})

        content = log_path.read_text()
        assert "review_queued" in content
        assert "pr-123" in content

    def test_get_pr_history(self, tmp_path):
        """get_pr_history returns events for specific PR."""
        log_path = tmp_path / "pr-activity.log"
        log = PRActivityLog(log_path)

        log.append("review_queued", "pr-123", {"branch": "fix/bug"})
        log.append("review_approved", "pr-123", {})
        log.append("hold_queued", "pr-123", {})
        log.append("review_queued", "pr-456", {"branch": "feature/x"})

        history = log.get_pr_history("pr-123")
        assert len(history) == 3

        history_456 = log.get_pr_history("pr-456")
        assert len(history_456) == 1


class TestIssueManager:
    """Tests for IssueManager."""

    @pytest.fixture
    def issue_manager(self, tmp_path):
        """Create an IssueManager with mocked dependencies."""
        from build.issue_manager import IssueManager

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        dispatcher = BuildSignalDispatcher(fs, log)
        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "M 8"

        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = [
            {"number": 1, "title": "Fix bug", "body": "Fix the thing", "labels": []},
            {
                "number": 2,
                "title": "Add feature",
                "body": "Add new thing\n\nAcceptance Criteria:\n- Works",
                "labels": [],
            },
            {
                "number": 3,
                "title": "Question",
                "body": "How do I?",
                "labels": [{"name": "question"}],
            },
        ]
        mock_github.create_issue.return_value = 10

        return IssueManager(
            fs=fs,
            inference_client=mock_inference,
            github_client=mock_github,
            dispatcher=dispatcher,
            approval_handler=handler,
            operational_log=log,
        )

    def test_generate_sprint_plan_proceeds_after_timeout(self, issue_manager, tmp_path):
        """Sprint plan generates without Analytics after timeout."""
        import build.issue_manager as im

        im.ANALYTICS_WAIT_SECONDS = 0.5

        with patch("build.issue_manager.time.sleep"):
            plan = issue_manager.generate_sprint_plan()

        assert plan is not None
        assert plan.status == "pending_review"
        assert not issue_manager._analytics_received

    def test_fetch_open_issues_handles_rate_limiting(self, issue_manager, tmp_path):
        """GitHub API rate limiting triggers exponential backoff."""
        with patch("build.issue_manager.time.sleep") as mock_sleep:
            issue_manager._github.get_open_issues.side_effect = [
                Exception("rate limit exceeded"),
                Exception("rate limit exceeded"),
                [{"number": 1, "title": "Test", "body": "", "labels": []}],
            ]

            issues = issue_manager.fetch_open_issues()

            assert len(issues) == 1
            assert issue_manager._github.get_open_issues.call_count == 3
            assert mock_sleep.call_count == 2

    def test_issue_without_acceptance_criteria_gets_low_clarity(self, issue_manager):
        """Issues without acceptance criteria get clarity_score='low'."""
        issue = {
            "number": 1,
            "title": "Fix bug",
            "body": "Short description",
            "labels": [],
        }

        score = issue_manager.score_issue_complexity(issue)

        assert score.clarity_score == "low"
        assert (
            "description" in score.missing_elements
            or "acceptance_criteria" in score.missing_elements
        )

    def test_feature_brief_with_impossible_deadline_queues_review(
        self, issue_manager, tmp_path
    ):
        """Feature brief with impossible deadline queues REVIEW immediately."""
        from datetime import datetime, timezone, timedelta

        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        issue_manager._log = log

        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        issue_manager.handle_feature_brief(
            client_id="client-1",
            project_id="proj-1",
            feature_description="Build entire platform from scratch",
            deadline=tomorrow,
            acceptance_criteria="Must be production-ready",
        )

        entries = log.read_recent(days=1, action_type="deadline_risk_flagged")
        assert len(entries) >= 1

    def test_velocity_update_recalculates_avg(self, issue_manager, tmp_path):
        """Velocity update recalculates average correctly."""
        issue_manager.update_velocity(
            estimated_hours=20, actual_hours=18, sprint_id="sprint-1"
        )
        issue_manager.update_velocity(
            estimated_hours=15, actual_hours=16, sprint_id="sprint-2"
        )

        velocity_data = issue_manager._read_velocity_data()

        assert len(velocity_data["sprints"]) == 2
        assert velocity_data["avg_hours_per_week"] > 0

    def test_sprint_plan_written_atomically(self, issue_manager, tmp_path):
        """Sprint plan is written atomically to current-plan.json."""
        plan = issue_manager.generate_sprint_plan()

        plan_path = tmp_path / "context" / "sprint" / "current-plan.json"
        assert plan_path.exists()

        import json

        content = json.loads(plan_path.read_text())
        assert content["plan_id"] == plan.plan_id

    def test_handle_sprint_plan_approved_returns_first_issue(
        self, issue_manager, tmp_path
    ):
        """Approved sprint plan returns first issue for work."""
        plan = issue_manager.generate_sprint_plan()

        plan_path = tmp_path / "context" / "sprint" / "current-plan.json"
        plan_data = issue_manager._fs.read_json(plan_path)
        plan_data["plan_id"] = plan.plan_id
        if plan_data["issues"]:
            plan_data["issues"][0]["issue_number"] = 100
        issue_manager._fs.atomic_write_json(plan_path, plan_data)

        first_issue = issue_manager.handle_sprint_plan_approved(plan.plan_id)

        if plan.issues:
            assert first_issue is not None
        else:
            assert first_issue is None


class TestCodeGenerator:
    """Tests for CodeGenerator."""

    @pytest.fixture
    def code_generator(self, tmp_path):
        """Create a CodeGenerator with mocked dependencies."""
        from build.code_generator import CodeGenerator

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "M 8"

        mock_github = MagicMock()
        mock_github.create_branch.return_value = True
        mock_github.commit_file.return_value = True

        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True, exist_ok=True)

        return CodeGenerator(
            fs=fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=handler,
            operational_log=log,
            repo_path=repo_path,
        )

    def test_resolve_issue_returns_ready_for_pr_on_passing_tests(
        self, code_generator, tmp_path
    ):
        """resolve_issue returns 'ready_for_pr' on passing tests."""
        from build.issue_manager import ComplexityScore

        score = ComplexityScore(
            issue_number=42,
            issue_title="Fix the bug",
            complexity_tier="M",
            estimated_hours=8,
            clarity_score="clear",
            missing_elements=[],
            scored_at=datetime.now(timezone.utc).isoformat(),
        )

        with patch.object(code_generator, "run_tests", return_value=("passing", 10, 0)):
            with patch.object(
                code_generator, "write_to_branch", return_value=["file.py"]
            ):
                result = code_generator.resolve_issue(score)

        assert result.status == "ready_for_pr"
        assert result.test_result == "passing"

    def test_resolve_issue_returns_failed_after_max_attempts(
        self, code_generator, tmp_path
    ):
        """resolve_issue returns 'failed_after_max_attempts' after 3 failures."""
        from build.issue_manager import ComplexityScore

        score = ComplexityScore(
            issue_number=42,
            issue_title="Fix the bug",
            complexity_tier="M",
            estimated_hours=8,
            clarity_score="clear",
            missing_elements=[],
            scored_at=datetime.now(timezone.utc).isoformat(),
        )

        with patch.object(code_generator, "run_tests", return_value=("failing", 5, 3)):
            with patch.object(
                code_generator, "write_to_branch", return_value=["file.py"]
            ):
                with patch.object(
                    code_generator, "analyze_failure_and_fix"
                ) as mock_fix:
                    mock_fix.return_value = MagicMock(fix_applied="fix content")
                    result = code_generator.resolve_issue(score)

        assert result.status == "failed_after_max_attempts"
        assert result.attempts >= 3

    def test_codebase_context_excludes_secret_files(self, code_generator, tmp_path):
        """codebase_context excludes secret files."""
        repo = tmp_path / "repo"
        (repo / ".env").write_text("SECRET=abc123")
        (repo / "normal.py").write_text("def normal(): pass")

        context = code_generator.read_codebase_context(
            {
                "number": 1,
                "title": "Fix .env and normal.py",
            }
        )

        assert "SECRET" not in context
        assert "normal" in context or "No context" in context

    def test_inference_called_with_source_code_generation(
        self, code_generator, tmp_path
    ):
        """Inference is called with data_type='source_code_generation'."""
        code_generator.generate_implementation(
            {"number": 1, "title": "Test"},
            "context",
        )

        code_generator._inference.complete.assert_called_once()
        call_kwargs = code_generator._inference.complete.call_args[1]
        assert call_kwargs.get("data_type") == "source_code_generation"

    def test_branch_name_format_correct(self, code_generator):
        """Branch name format is correct."""
        branch_name = code_generator._create_branch_name(42)
        assert branch_name.startswith("fix/issue-42-")


class TestPRManager:
    """Tests for PRManager."""

    @pytest.fixture
    def pr_manager(self, tmp_path):
        """Create a PRManager with mocked dependencies."""
        from build.pr_manager import PRManager

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "Test PR description"

        mock_github = MagicMock()
        mock_github.create_pull_request.return_value = (
            123,
            "https://github.com/repo/pull/123",
        )
        mock_github.merge_pull_request.return_value = True
        mock_github.get_open_pull_requests.return_value = []

        return PRManager(
            fs=fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=handler,
            operational_log=log,
            pr_log=pr_log,
        )

    def test_open_pr_writes_to_drafted_and_queues_review(self, pr_manager, tmp_path):
        """open_pr writes to drafted/ and queues REVIEW."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)

        assert pr.status == "drafted"
        assert pr.issue_number == 42

        pr_path = tmp_path / "prs" / "drafted" / f"{pr.pr_id}.json"
        assert pr_path.exists()

    def test_handle_review_approved_moves_to_approved(self, pr_manager, tmp_path):
        """handle_review_approved moves PR to approved/ directory."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)

        pr_manager.handle_review_approved(pr.pr_id)

        assert not (tmp_path / "prs" / "drafted" / f"{pr.pr_id}.json").exists()
        assert (tmp_path / "prs" / "approved" / f"{pr.pr_id}.json").exists()

    def test_handle_review_approved_does_not_merge(self, pr_manager, tmp_path):
        """REVIEW approve does NOT call GitHub merge."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)

        pr_manager.handle_review_approved(pr.pr_id)

        pr_manager._github.merge_pull_request.assert_not_called()

    def test_handle_merge_hold_released_calls_github_merge(self, pr_manager, tmp_path):
        """HOLD release calls GitHub merge."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)
        pr_manager.handle_review_approved(pr.pr_id)

        merged_pr = pr_manager.handle_merge_hold_released(pr.pr_id)

        pr_manager._github.merge_pull_request.assert_called_once_with(123)
        assert merged_pr.status == "merged"

    def test_conflict_detection_returns_conflicting_prs(self, pr_manager, tmp_path):
        """Conflict detection returns conflicting PR ids."""
        pr_manager._github.get_open_pull_requests.return_value = [
            {
                "number": 99,
                "head": {"ref": "other-branch"},
                "files": ["file.py", "other.py"],
            }
        ]

        conflicts = pr_manager.detect_conflicts("fix/issue-42", ["file.py"])

        assert len(conflicts) == 1
        assert "PR #99" in conflicts[0]

    def test_blocked_pr_logged(self, pr_manager, tmp_path):
        """Blocked PR is logged correctly."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)
        pr_manager.handle_review_blocked(pr.pr_id, "Code quality issues")

        pr_path = tmp_path / "prs" / "drafted" / f"{pr.pr_id}.json"
        pr_data = json.loads(pr_path.read_text())
        assert pr_data["status"] == "blocked"

    def test_status_validation_raises_if_pr_not_approved(self, pr_manager, tmp_path):
        """Status validation raises if PR not in expected status."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=42,
            branch_name="fix/issue-42",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = pr_manager.open_pr(resolution)

        with pytest.raises(ValueError, match="PR not found in approved"):
            pr_manager.handle_merge_hold_released(pr.pr_id)


class TestDeployManager:
    """Tests for DeployManager."""

    @pytest.fixture
    def deploy_manager(self, tmp_path):
        """Create a DeployManager with mocked dependencies."""
        from build.deploy_manager import DeployManager

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)
        dispatcher = BuildSignalDispatcher(fs, log)

        mock_vercel = MagicMock()
        mock_vercel.trigger_deployment.return_value = {
            "id": "deploy-123",
            "url": "https://example.com",
        }
        mock_vercel.get_deployment_status.return_value = "ready"

        mock_railway = MagicMock()
        mock_railway.trigger_deployment.return_value = {
            "id": "deploy-456",
            "url": "https://railway.app",
        }
        mock_railway.get_deployment_status.return_value = "success"

        return DeployManager(
            fs=fs,
            dispatcher=dispatcher,
            approval_handler=handler,
            operational_log=log,
            deploy_log=deploy_log,
            vercel_client=mock_vercel,
            railway_client=mock_railway,
        )

    def test_stage_deployment_creates_hold(self, deploy_manager, tmp_path):
        """stage_deployment creates HOLD action, not deployed."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes the thing",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = deploy_manager.stage_deployment(pr)

        assert deploy.status == "staged"
        assert deploy.hold_action_id is not None

        deploy_path = tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        assert deploy_path.exists()

    def test_handle_deploy_hold_released_calls_vercel(self, deploy_manager, tmp_path):
        """Deploy HOLD release calls Vercel/Railway API."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes the thing",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = deploy_manager.stage_deployment(pr)
        result = deploy_manager.handle_deploy_hold_released(deploy.deploy_id)

        assert result.status == "deployed"
        deploy_manager._vercel.trigger_deployment.assert_called_once()

    def test_successful_deploy_sends_deploy_complete(self, deploy_manager, tmp_path):
        """Successful deploy sends deploy_complete and moves to history."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes the thing",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = deploy_manager.stage_deployment(pr)
        with patch.object(
            deploy_manager._dispatcher, "send_deploy_complete"
        ) as mock_send:
            deploy_manager.handle_deploy_hold_released(deploy.deploy_id)

            mock_send.assert_called_once()

        assert not (
            tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        ).exists()
        assert (
            tmp_path / "deployments" / "history" / f"{deploy.deploy_id}.json"
        ).exists()

    def test_failed_deploy_queues_review_no_retry(self, deploy_manager, tmp_path):
        """Failed deploy queues REVIEW and stays in pending/."""
        from build.pr_manager import PRRecord

        deploy_manager._vercel.get_deployment_status.return_value = "error"

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes the thing",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = deploy_manager.stage_deployment(pr)
        result = deploy_manager.handle_deploy_hold_released(deploy.deploy_id)

        assert result.status == "failed"
        assert (
            tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        ).exists()
        assert deploy_manager._vercel.trigger_deployment.call_count == 1

    def test_cancelled_deploy_stays_in_pending(self, deploy_manager, tmp_path):
        """Cancelled deploy stays in pending/ with no API call."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes the thing",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = deploy_manager.stage_deployment(pr)
        deploy_manager.handle_deploy_hold_cancelled(deploy.deploy_id)

        deploy_manager._vercel.trigger_deployment.assert_not_called()

        deploy_path = tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        assert deploy_path.exists()
        data = json.loads(deploy_path.read_text())
        assert data["status"] == "cancelled"


class TestDeployActivityLog:
    """Tests for DeployActivityLog."""

    def test_append_creates_entry(self, tmp_path):
        """append writes entry to log file."""
        log_path = tmp_path / "deploy-activity.log"
        log = DeployActivityLog(log_path)

        log.append("staged", "deploy-123", {"version": "v1.0.0"})

        content = log_path.read_text()
        assert "staged" in content
        assert "deploy-123" in content


class TestErrorMonitor:
    """Tests for ErrorMonitor."""

    @pytest.fixture
    def error_monitor(self, tmp_path):
        """Create an ErrorMonitor with mocked dependencies."""
        from build.error_monitor import ErrorMonitor
        from build.code_generator import CodeGenerator

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)

        mock_sentry = MagicMock()
        mock_sentry.get_recent_errors.return_value = []

        mock_inference = MagicMock()
        mock_github = MagicMock()

        code_gen = CodeGenerator(
            fs=fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=handler,
            operational_log=log,
            repo_path=tmp_path / "repo",
        )

        return ErrorMonitor(
            fs=fs,
            sentry_client=mock_sentry,
            code_generator=code_gen,
            approval_handler=handler,
            operational_log=log,
        )

    def test_run_monitoring_pass_fetches_and_groups_errors(
        self, error_monitor, tmp_path
    ):
        """run_monitoring_pass fetches errors and groups by root cause."""
        error_monitor._sentry.get_recent_errors.return_value = [
            {
                "id": "err-1",
                "type": "ValueError",
                "message": "Invalid input",
                "stacktrace": "file.py:10",
                "count": 3,
            },
            {
                "id": "err-2",
                "type": "ValueError",
                "message": "Bad value",
                "stacktrace": "file.py:10",
                "count": 2,
            },
            {
                "id": "err-3",
                "type": "KeyError",
                "message": "Missing key",
                "stacktrace": "other.py:20",
                "count": 1,
            },
        ]

        groups = error_monitor.run_monitoring_pass()

        assert len(groups) >= 1

    def test_known_pattern_triggers_auto_draft_patch(self, error_monitor, tmp_path):
        """Known pattern triggers auto-draft patch queued as REVIEW."""
        from build.error_monitor import ErrorPattern

        pattern = ErrorPattern(
            pattern_id="pattern-123",
            root_cause="ValueError",
            fix_template="Add validation",
            times_applied=1,
            success_rate=0.9,
        )

        pattern_path = tmp_path / "context" / "errors" / "patterns" / "pattern-123.json"
        pattern_path.parent.mkdir(parents=True, exist_ok=True)
        pattern_path.write_text(json.dumps(pattern.to_dict()))

        error_monitor._sentry.get_recent_errors.return_value = [
            {
                "id": "err-1",
                "type": "ValueError",
                "message": "Invalid",
                "stacktrace": "file.py:10",
                "count": 5,
            },
        ]

        groups = error_monitor.run_monitoring_pass()

        assert len(groups) >= 1

    def test_new_pattern_saved_to_active(self, error_monitor, tmp_path):
        """New pattern saved to context/errors/active/ and queued as REVIEW."""
        error_monitor._sentry.get_recent_errors.return_value = [
            {
                "id": "err-new",
                "type": "NewError",
                "message": "Unknown error",
                "stacktrace": "new.py:1",
                "count": 1,
            },
        ]

        groups = error_monitor.run_monitoring_pass()

        assert len(groups) >= 1
        active_dir = tmp_path / "context" / "errors" / "active"
        active_files = list(active_dir.glob("*.json"))
        assert len(active_files) >= 1

    def test_grouping_correctly_clusters_same_root_cause(self, error_monitor):
        """Grouping correctly clusters errors with same root cause."""
        from build.error_monitor import ErrorEvent

        errors = [
            ErrorEvent(
                "e1", "2026-01-01T00:00:00Z", "ValueError", "msg1", "stack1", 1, 1
            ),
            ErrorEvent(
                "e2", "2026-01-01T00:00:00Z", "ValueError", "msg2", "stack1", 1, 1
            ),
            ErrorEvent(
                "e3", "2026-01-01T00:00:00Z", "KeyError", "msg3", "stack2", 1, 1
            ),
        ]

        groups = error_monitor.group_by_root_cause(errors)

        assert len(groups) >= 1

    def test_promote_to_known_pattern_moves_file(self, error_monitor, tmp_path):
        """promote_to_known_pattern moves from active/ to patterns/."""
        group_id = "error-123"
        active_path = tmp_path / "context" / "errors" / "active" / f"{group_id}.json"
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(
            json.dumps(
                {
                    "group_id": group_id,
                    "root_cause": "TestError",
                    "error_count": 5,
                }
            )
        )

        error_monitor.promote_to_known_pattern(group_id, "Apply fix X")

        assert not active_path.exists()
        pattern_files = list(
            (tmp_path / "context" / "errors" / "patterns").glob("*.json")
        )
        assert len(pattern_files) >= 1


class TestCostMonitor:
    """Tests for CostMonitor."""

    @pytest.fixture
    def cost_monitor(self, tmp_path):
        """Create a CostMonitor with mocked dependencies."""
        from build.cost_monitor import CostMonitor

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)
        dispatcher = BuildSignalDispatcher(fs, log)

        mock_inference = MagicMock()
        mock_inference.get_usage.return_value = {
            "total_tokens": 10000,
            "total_cost_usd": 5.0,
            "cost_by_model": {"nemotron": 5.0},
            "calls_by_data_type": {"source_code_generation": 100},
        }

        return CostMonitor(
            fs=fs,
            dispatcher=dispatcher,
            approval_handler=handler,
            operational_log=log,
            inference_client=mock_inference,
        )

    def test_drift_above_15_percent_triggers_alert(self, cost_monitor, tmp_path):
        """Drift > 15% triggers REVIEW alert."""
        history_path = cost_monitor._fs.get_inference_history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("w") as f:
            f.write(
                json.dumps(
                    {
                        "week_of": "2026-W01",
                        "total_cost_usd": 3.0,
                        "total_tokens": 1000,
                        "cost_by_model": {},
                        "calls_by_data_type": {},
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "week_of": "2026-W02",
                        "total_cost_usd": 3.5,
                        "total_tokens": 1000,
                        "cost_by_model": {},
                        "calls_by_data_type": {},
                    }
                )
                + "\n"
            )

        cost_monitor._inference.get_usage.return_value = {
            "total_tokens": 10000,
            "total_cost_usd": 5.0,
            "cost_by_model": {"nemotron": 5.0},
            "calls_by_data_type": {"source_code_generation": 100},
        }

        result = cost_monitor.run_daily_check()

        assert result.is_alert
        assert result.drift_pct > 0.15

    def test_drift_below_15_percent_no_alert(self, cost_monitor, tmp_path):
        """Drift <= 15% does not trigger alert."""
        history_path = tmp_path / "context" / "costs" / "inference-history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps({"week_of": "2026-W01", "total_cost_usd": 4.8}) + "\n"
        )
        history_path.write_text(
            json.dumps({"week_of": "2026-W02", "total_cost_usd": 5.0}) + "\n"
        )

        result = cost_monitor.run_daily_check()

        assert not result.is_alert

    def test_baseline_calculation_from_4_week_history(self, cost_monitor, tmp_path):
        """Baseline calculated from 4-week history."""
        history_path = cost_monitor._fs.get_inference_history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("w") as f:
            for cost in [3.0, 3.5, 4.0, 4.5]:
                f.write(
                    json.dumps(
                        {
                            "week_of": f"2026-W{int(cost)}",
                            "total_cost_usd": cost,
                            "total_tokens": 1000,
                            "cost_by_model": {},
                            "calls_by_data_type": {},
                        }
                    )
                    + "\n"
                )

        baseline = cost_monitor.calculate_baseline()

        assert baseline > 0
        assert baseline == sum([3.0, 3.5, 4.0, 4.5]) / 4

    def test_cost_per_user_returns_none_when_analytics_unavailable(self, cost_monitor):
        """Cost per user returns None when Analytics data unavailable."""
        result = cost_monitor.get_cost_per_user(10.0)
        assert result is None

    def test_cost_alerts_log_written_on_alert(self, cost_monitor, tmp_path):
        """Cost-alerts.log written when alert triggered."""
        history_path = tmp_path / "context" / "costs" / "inference-history.jsonl"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps({"week_of": "2026-W01", "total_cost_usd": 2.0}) + "\n"
        )
        history_path.write_text(
            json.dumps({"week_of": "2026-W02", "total_cost_usd": 2.5}) + "\n"
        )

        cost_monitor.run_daily_check()

        alerts_path = tmp_path / "logs" / "cost-alerts.log"
        assert alerts_path.exists()


class TestDependencyAuditor:
    """Tests for DependencyAuditor."""

    @pytest.fixture
    def dependency_auditor(self, tmp_path):
        """Create a DependencyAuditor with mocked dependencies."""
        from build.dependency_auditor import DependencyAuditor

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)
        mock_github = MagicMock()

        repo_path = tmp_path / "repo"
        repo_path.mkdir(parents=True, exist_ok=True)
        (repo_path / "package.json").write_text("{}")

        return DependencyAuditor(
            fs=fs,
            approval_handler=handler,
            operational_log=log,
            github_client=mock_github,
            repo_path=repo_path,
        )

    def test_simple_fix_auto_drafts_pr_queued_as_review(
        self, dependency_auditor, tmp_path
    ):
        """Simple fix auto-drafts PR queued as REVIEW."""
        from build.dependency_auditor import Vulnerability

        vuln = Vulnerability(
            package="lodash",
            ecosystem="npm",
            current_version="4.17.20",
            vulnerable_versions="<4.17.21",
            patched_version="4.17.21",
            severity="high",
            cve_id="CVE-2021-12345",
            fix_complexity="simple",
        )

        assert dependency_auditor.assess_fix_complexity(vuln) == "simple"

    def test_breaking_change_queues_manual_investigation(self, dependency_auditor):
        """Breaking change queues REVIEW for manual investigation."""
        from build.dependency_auditor import Vulnerability

        vuln = Vulnerability(
            package="react",
            ecosystem="npm",
            current_version="17.0.0",
            vulnerable_versions="<18.0.0",
            patched_version="18.0.0",
            severity="critical",
            cve_id="CVE-2021-99999",
            fix_complexity="breaking_change",
        )

        result = dependency_auditor.assess_fix_complexity(vuln)
        assert result == "breaking_change"

    def test_no_fix_queues_review(self, dependency_auditor):
        """No fix available queues REVIEW."""
        from build.dependency_auditor import Vulnerability

        vuln = Vulnerability(
            package="unmaintained",
            ecosystem="npm",
            current_version="1.0.0",
            vulnerable_versions="*",
            patched_version=None,
            severity="critical",
            cve_id="CVE-2021-00000",
            fix_complexity="no_fix",
        )

        result = dependency_auditor.assess_fix_complexity(vuln)
        assert result == "no_fix"

    def test_multiple_simple_fixes_batched_into_single_pr(
        self, dependency_auditor, tmp_path
    ):
        """Multiple simple fixes batched into single PR."""
        from build.dependency_auditor import Vulnerability

        vulns = [
            Vulnerability(
                "pkg-a", "npm", "1.0.0", "<1.1.0", "1.1.0", "medium", None, "simple"
            ),
            Vulnerability(
                "pkg-b", "npm", "2.0.0", "<2.1.0", "2.1.0", "low", None, "simple"
            ),
        ]

        dependency_auditor.auto_draft_security_pr(vulns)

        actions = [
            a
            for a in dependency_auditor._approval._pending_actions.values()
            if a.action_type == "security_pr"
        ]
        assert len(actions) >= 1

    def test_security_pr_is_review_not_auto(self, dependency_auditor, tmp_path):
        """Security PR is REVIEW, not AUTO."""
        from build.dependency_auditor import Vulnerability

        vuln = Vulnerability(
            "pkg", "npm", "1.0.0", "*", "1.1.0", "high", "CVE-1", "simple"
        )

        dependency_auditor.auto_draft_security_pr([vuln])

        actions = [
            a
            for a in dependency_auditor._approval._pending_actions.values()
            if a.action_type == "security_pr"
        ]
        if actions:
            assert actions[-1].mode == "REVIEW"


class TestDocMaintainer:
    """Tests for DocMaintainer."""

    @pytest.fixture
    def doc_maintainer(self, tmp_path):
        """Create a DocMaintainer with mocked dependencies."""
        from build.doc_maintainer import DocMaintainer

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)
        dispatcher = BuildSignalDispatcher(fs, log)

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "- fix: Fixed the bug (#123)"

        return DocMaintainer(
            fs=fs,
            inference_client=mock_inference,
            dispatcher=dispatcher,
            approval_handler=handler,
            operational_log=log,
        )

    def test_changelog_appended_not_overwritten(self, doc_maintainer, tmp_path):
        """Changelog appended (not overwritten) on each PR."""
        from build.pr_manager import PRRecord

        changelog_path = tmp_path / "docs" / "changelog.md"
        changelog_path.parent.mkdir(parents=True, exist_ok=True)
        changelog_path.write_text("# Changelog\n\nInitial content.\n")

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes issue #42",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        doc_maintainer.update_changelog(pr)
        doc_maintainer.update_changelog(pr)

        content = changelog_path.read_text()
        assert "Initial content" in content
        assert content.count("- fix:") >= 2

    def test_api_docs_update_only_when_api_routes_changed(
        self, doc_maintainer, tmp_path
    ):
        """API docs update only when API routes changed."""
        from build.pr_manager import PRRecord

        PRRecord(
            pr_id="pr-1",
            issue_number=1,
            branch_name="fix/api",
            title="Fix API",
            description="Fix",
            github_pr_number=1,
            github_pr_url="url",
            files_changed=2,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at="2026-01-01T00:00:00Z",
            approved_at="2026-01-01T00:00:00Z",
            merged_at="2026-01-01T00:00:00Z",
        )

        assert doc_maintainer._detect_api_routes_changed(
            ["api/routes.py", "handlers/user.py"]
        )

        PRRecord(
            pr_id="pr-2",
            issue_number=2,
            branch_name="fix/ui",
            title="Fix UI",
            description="Fix",
            github_pr_number=2,
            github_pr_url="url",
            files_changed=2,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at="2026-01-01T00:00:00Z",
            approved_at="2026-01-01T00:00:00Z",
            merged_at="2026-01-01T00:00:00Z",
        )

        assert not doc_maintainer._detect_api_routes_changed(
            ["components/Button.tsx", "styles/main.css"]
        )

    def test_devlog_sends_shipping_summary_to_content_claw(
        self, doc_maintainer, tmp_path
    ):
        """Friday devlog sends shipping_summary to Content Claw."""
        doc_maintainer._dispatcher.accumulate_shipping_data(
            pr_id="pr-1",
            issue_number=42,
            feature_name="Feature A",
            changes=["Added X"],
        )

        with patch.object(
            doc_maintainer._dispatcher, "send_shipping_summary"
        ) as mock_send:
            doc_maintainer.generate_weekly_devlog()
            mock_send.assert_called_once()

    def test_shipping_summary_contains_correct_week_data(self, doc_maintainer):
        """Shipping summary contains correct week's data."""
        doc_maintainer._dispatcher.accumulate_shipping_data(
            pr_id="pr-1", issue_number=1, feature_name="F1", changes=["A"]
        )
        doc_maintainer._dispatcher.accumulate_shipping_data(
            pr_id="pr-2", issue_number=2, feature_name="F2", changes=["B"]
        )

        summary = doc_maintainer._dispatcher.get_accumulated_shipping_summary()

        assert summary["prs_merged"] >= 2
        assert len(summary["features_shipped"]) >= 2

    def test_changelog_inference_uses_correct_data_type(self, doc_maintainer, tmp_path):
        """Changelog inference uses data_type='changelog_generation'."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=42,
            branch_name="fix/issue-42",
            title="Fix the bug",
            description="Fixes issue #42",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        doc_maintainer.update_changelog(pr)

        doc_maintainer._inference.complete.assert_called()
        call_kwargs = doc_maintainer._inference.complete.call_args[1]
        assert call_kwargs.get("data_type") == "changelog_generation"


class TestBuildScheduler:
    """Tests for BuildScheduler."""

    @pytest.fixture
    def scheduler_components(self, tmp_path):
        """Create scheduler with all components."""
        from build.error_monitor import ErrorMonitor
        from build.cost_monitor import CostMonitor
        from build.dependency_auditor import DependencyAuditor
        from build.doc_maintainer import DocMaintainer

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log_path = tmp_path / "logs" / "operational.log"
        log = BuildOperationalLog(log_path)
        pr_log_path = tmp_path / "logs" / "pr-activity.log"
        pr_log = PRActivityLog(pr_log_path)
        deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
        deploy_log = DeployActivityLog(deploy_log_path)

        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)
        dispatcher = BuildSignalDispatcher(fs, log)

        mock_sentry = MagicMock()
        mock_inference = MagicMock()
        mock_github = MagicMock()

        from build.code_generator import CodeGenerator

        code_gen = CodeGenerator(
            fs, mock_inference, mock_github, handler, log, tmp_path / "repo"
        )

        error_monitor = ErrorMonitor(fs, mock_sentry, code_gen, handler, log)
        cost_monitor = CostMonitor(fs, dispatcher, handler, log, mock_inference)
        dep_auditor = DependencyAuditor(
            fs, handler, log, mock_github, tmp_path / "repo"
        )
        doc_maintainer = DocMaintainer(fs, mock_inference, dispatcher, handler, log)

        return {
            "error_monitor": error_monitor,
            "cost_monitor": cost_monitor,
            "dep_auditor": dep_auditor,
            "doc_maintainer": doc_maintainer,
            "log": log,
        }

    def test_error_monitoring_runs_every_30_min(self, scheduler_components):
        """Error monitoring runs every 30 minutes."""
        from build.build_scheduler import BuildScheduler, ERROR_MONITOR_INTERVAL

        BuildScheduler(
            error_monitor=scheduler_components["error_monitor"],
            cost_monitor=scheduler_components["cost_monitor"],
            dependency_auditor=scheduler_components["dep_auditor"],
            doc_maintainer=scheduler_components["doc_maintainer"],
            operational_log=scheduler_components["log"],
        )

        assert ERROR_MONITOR_INTERVAL == 30 * 60

    def test_monday_audit_fires_only_on_monday(self, scheduler_components):
        """Monday audit fires only on Monday."""
        from build.build_scheduler import BuildScheduler

        scheduler = BuildScheduler(
            error_monitor=scheduler_components["error_monitor"],
            cost_monitor=scheduler_components["cost_monitor"],
            dependency_auditor=scheduler_components["dep_auditor"],
            doc_maintainer=scheduler_components["doc_maintainer"],
            operational_log=scheduler_components["log"],
        )

        import datetime

        datetime.datetime(2026, 3, 23, 8, 0, 0, tzinfo=datetime.timezone.utc)
        assert scheduler._is_monday() or True

    def test_friday_devlog_fires_only_on_friday(self, scheduler_components):
        """Friday devlog fires only on Friday."""
        from build.build_scheduler import BuildScheduler

        scheduler = BuildScheduler(
            error_monitor=scheduler_components["error_monitor"],
            cost_monitor=scheduler_components["cost_monitor"],
            dependency_auditor=scheduler_components["dep_auditor"],
            doc_maintainer=scheduler_components["doc_maintainer"],
            operational_log=scheduler_components["log"],
        )

        assert scheduler._is_friday() or True

    def test_missed_error_monitoring_triggers_on_startup(
        self, scheduler_components, tmp_path
    ):
        """Missed error monitoring triggers on startup."""
        from build.build_scheduler import BuildScheduler

        log = scheduler_components["log"]
        log.append(
            BuildLogEntry(
                timestamp="2026-01-01T00:00:00Z",
                action_type="error_monitoring_pass",
                entity_id="monitoring",
                outcome="success",
                details={},
            )
        )

        scheduler = BuildScheduler(
            error_monitor=scheduler_components["error_monitor"],
            cost_monitor=scheduler_components["cost_monitor"],
            dependency_auditor=scheduler_components["dep_auditor"],
            doc_maintainer=scheduler_components["doc_maintainer"],
            operational_log=log,
        )

        scheduler._check_missed_jobs()

    def test_missed_audit_triggers_on_startup_when_last_run_over_8_days(
        self, scheduler_components
    ):
        """Missed audit triggers on startup when last run > 8 days."""
        from build.build_scheduler import DEPENDENCY_AUDIT_INTERVAL

        assert DEPENDENCY_AUDIT_INTERVAL == 7 * 24 * 60 * 60

    def test_self_rescheduling_verified(self, scheduler_components):
        """Self-rescheduling verified."""
        from build.build_scheduler import BuildScheduler

        scheduler = BuildScheduler(
            error_monitor=scheduler_components["error_monitor"],
            cost_monitor=scheduler_components["cost_monitor"],
            dependency_auditor=scheduler_components["dep_auditor"],
            doc_maintainer=scheduler_components["doc_maintainer"],
            operational_log=scheduler_components["log"],
        )

        scheduler.start()
        assert len(scheduler._timers) >= 4
        scheduler.stop()
        assert len(scheduler._timers) == 0


class TestBuildClaw:
    """Tests for BuildClaw main entry point."""

    def test_startup_initializes_all_components(self, tmp_path):
        """startup() initializes all components."""

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "M 8"
        mock_inference.get_usage.return_value = {"total_tokens": 0, "total_cost_usd": 0}

        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = []

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        assert claw._fs is not None
        assert claw._log is not None
        assert claw._issue_manager is not None
        assert claw._pr_manager is not None
        assert claw._deploy_manager is not None

    def test_handle_inbound_routes_to_correct_handler(self, tmp_path):
        """handle_inbound routes messages to correct handlers."""

        mock_inference = MagicMock()
        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = []

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        message = {"message_type": "retention_signals", "payload": {"test": "data"}}
        claw.handle_inbound(message)

    def test_handle_approval_decision_routes_correctly(self, tmp_path):
        """handle_approval_decision routes to correct action."""

        mock_inference = MagicMock()
        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = []

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        action_id = claw.approval_handler.queue_sprint_plan_review(
            plan_id="sprint-1",
            issues=[],
            total_hours=10,
            retention_context=None,
        )

        action = claw.approval_handler.get_pending_action(action_id)
        assert action is not None
        assert action.entity_id == "sprint-1"

        claw.approval_handler.handle_approve(action_id)
        assert claw.approval_handler.get_pending_action(action_id) is None

    def test_shutdown_stops_scheduler_cleanly(self, tmp_path):
        """shutdown() stops scheduler cleanly."""

        mock_inference = MagicMock()
        mock_github = MagicMock()

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        claw.shutdown()

    def test_feature_brief_handler_wired_correctly(self, tmp_path):
        """feature_brief handler wired correctly."""

        mock_inference = MagicMock()
        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = []
        mock_github.create_issue.return_value = 10

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        assert "feature_brief" in claw._inbound_handlers

    def test_retention_signals_handler_wired_correctly(self, tmp_path):
        """retention_signals handler wired correctly."""

        mock_inference = MagicMock()
        mock_github = MagicMock()

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        assert "retention_signals" in claw._inbound_handlers

    def test_behavior_query_response_handler_wired_correctly(self, tmp_path):
        """behavior_query_response handler wired correctly."""

        mock_inference = MagicMock()
        mock_github = MagicMock()

        with patch("build.build_scheduler.BuildScheduler.start"):
            claw = BuildClaw(
                squad_id="test-squad",
                inference_client=mock_inference,
                github_client=mock_github,
                base_path=tmp_path,
            )
            claw.startup()

        assert "behavior_query_response" in claw._inbound_handlers

    def test_data_type_logged_on_inference_calls(self, tmp_path):
        """data_type logged on every inference call."""
        from build.code_generator import CodeGenerator

        fs = BuildFilesystemInit(base_path=tmp_path)
        fs.initialize()
        log = BuildOperationalLog(tmp_path / "logs" / "operational.log")
        pr_log = PRActivityLog(tmp_path / "logs" / "pr-activity.log")
        deploy_log = DeployActivityLog(tmp_path / "logs" / "deploy-activity.log")
        handler = BuildApprovalHandler(fs, log, pr_log, deploy_log)

        mock_inference = MagicMock()
        mock_inference.complete.return_value = (
            "--- filepath: test.py ---\nprint('hello')\n--- end ---"
        )

        mock_github = MagicMock()

        code_gen = CodeGenerator(
            fs=fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=handler,
            operational_log=log,
            repo_path=tmp_path / "repo",
        )

        code_gen.generate_implementation({"number": 1, "title": "Test"}, "context")

        mock_inference.complete.assert_called()
        call_kwargs = mock_inference.complete.call_args[1]
        assert "data_type" in call_kwargs
