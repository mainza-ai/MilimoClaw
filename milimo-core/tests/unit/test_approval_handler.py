"""Unit tests for OpsApprovalHandler."""

import json
import pytest
from unittest.mock import patch, mock_open
from milimo_core.ops.approval_handler import OpsApprovalHandler, OpsApprovalAction


class TestOpsApprovalAction:
    """Tests for OpsApprovalAction dataclass."""

    def test_action_creation(self):
        """Test creating an OpsApprovalAction."""
        action = OpsApprovalAction(
            action_id="test-123",
            action_type="deploy",
            entity_id="production",
            mode="HOLD",
            content="Deploy new version",
            context={"version": "1.2.3"},
            timestamp="2024-01-01T00:00:00Z",
        )

        assert action.action_id == "test-123"
        assert action.action_type == "deploy"
        assert action.entity_id == "production"
        assert action.mode == "HOLD"
        assert action.content == "Deploy new version"
        assert action.context == {"version": "1.2.3"}
        assert action.outcome is None

    def test_action_to_dict(self):
        """Test action to_dict serialization."""
        action = OpsApprovalAction(
            action_id="test-123",
            action_type="deploy",
            entity_id="production",
            mode="HOLD",
            content="Deploy new version",
            context={"version": "1.2.3"},
        )

        data = action.to_dict()

        assert data["action_id"] == "test-123"
        assert data["action_type"] == "deploy"
        assert data["entity_id"] == "production"
        assert data["mode"] == "HOLD"
        assert data["content"] == "Deploy new version"
        assert data["context"] == {"version": "1.2.3"}

    def test_action_from_dict(self):
        """Test action from_dict deserialization."""
        data = {
            "action_id": "test-123",
            "action_type": "deploy",
            "entity_id": "production",
            "mode": "HOLD",
            "content": "Deploy new version",
            "context": {"version": "1.2.3"},
            "timestamp": "2024-01-01T00:00:00Z",
            "outcome": "approved",
            "hours_waiting": 24.0,
            "urgency_flag": "No decision in 24h",
        }

        action = OpsApprovalAction.from_dict(data)

        assert action.action_id == "test-123"
        assert action.outcome == "approved"
        assert action.hours_waiting == 24.0
        assert action.urgency_flag == "No decision in 24h"


class TestOpsApprovalHandler:
    """Tests for OpsApprovalHandler."""

    def test_initialization(self, approval_handler):
        """Test OpsApprovalHandler initialization."""
        assert approval_handler._fs_base is not None
        assert approval_handler._review_queue_dir.exists()
        assert approval_handler._hold_queue_dir.exists()

    def test_queue_hold(self, approval_handler):
        """Test queuing a HOLD item."""
        action_id = approval_handler.queue_hold(
            action_type="deploy",
            entity_id="production",
            content="Deploy new version",
            context={"version": "1.2.3"}
        )

        assert action_id is not None
        assert len(action_id) > 0

        hold_items = approval_handler.get_hold_queue()
        assert len(hold_items) == 1
        assert hold_items[0].action_id == action_id
        assert hold_items[0].action_type == "deploy"
        assert hold_items[0].entity_id == "production"
        assert hold_items[0].mode == "HOLD"

    def test_queue_review(self, approval_handler):
        """Test queuing a REVIEW item."""
        action_id = approval_handler.queue_review(
            action_type="update_config",
            entity_id="stripe",
            content="Update API keys",
            context={"keys": ["sk_test"]}
        )

        assert action_id is not None

        review_items = approval_handler.get_review_queue()
        assert len(review_items) == 1
        assert review_items[0].action_id == action_id
        assert review_items[0].action_type == "update_config"
        assert review_items[0].mode == "REVIEW"

    def test_get_hold_queue_empty(self, approval_handler):
        """Test getting empty HOLD queue."""
        items = approval_handler.get_hold_queue()
        assert items == []

    def test_get_review_queue_empty(self, approval_handler):
        """Test getting empty REVIEW queue."""
        items = approval_handler.get_review_queue()
        assert items == []

    def test_handle_approve_review(self, approval_handler):
        """Test approving a REVIEW item."""
        action_id = approval_handler.queue_review("update", "config", "Update config", {})

        # Mock send function
        sent = []
        def send_fn():
            sent.append(True)

        result = approval_handler.handle_approve(action_id, send_fn)

        assert result is True
        assert len(sent) == 1

        review_items = approval_handler.get_review_queue()
        assert len(review_items) == 0

    def test_handle_approve_hold(self, approval_handler):
        """Test approving a HOLD item (releases hold)."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        executed = []
        def execute_fn():
            executed.append(True)

        result = approval_handler.handle_hold_release(action_id, execute_fn)

        assert result is True
        assert len(executed) == 1

        hold_items = approval_handler.get_hold_queue()
        assert len(hold_items) == 0

    def test_handle_block(self, approval_handler):
        """Test blocking/rejecting an action."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        result = approval_handler.handle_block(action_id, reason="Invalid config")

        assert result is True

        review_items = approval_handler.get_review_queue()
        assert len(review_items) == 0

    def test_approve_nonexistent(self, approval_handler):
        """Test approving non-existent item."""
        result = approval_handler.handle_approve("nonexistent", lambda: None)
        assert result is False

    def test_block_nonexistent(self, approval_handler):
        """Test blocking non-existent item."""
        result = approval_handler.handle_block("nonexistent")
        assert result is False

    def test_add_urgency_flag(self, approval_handler):
        """Test adding urgency flag to HOLD item."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        result = approval_handler.add_urgency_flag(action_id, 24)

        assert result is True

        hold_items = approval_handler.get_hold_queue()
        assert hold_items[0].urgency_flag == "No decision in 24h — client may disengage"
        assert hold_items[0].hours_waiting == 24.0

    def test_add_urgency_flag_48_hours(self, approval_handler):
        """Test adding urgency flag at 48 hours."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        result = approval_handler.add_urgency_flag(action_id, 48)

        assert result is True

        review_items = approval_handler.get_review_queue()
        assert review_items[0].urgency_flag == "Response window closing"
        assert review_items[0].hours_waiting == 48.0

    def test_add_urgency_flag_nonexistent(self, approval_handler):
        """Test adding urgency flag to non-existent item."""
        result = approval_handler.add_urgency_flag("nonexistent", 24)
        assert result is False

    def test_get_action_by_id(self, approval_handler):
        """Test getting action by ID from either queue."""
        hold_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})
        review_id = approval_handler.queue_review("update", "config", "Update", {})

        hold_action = approval_handler.get_action(hold_id)
        assert hold_action is not None
        assert hold_action.mode == "HOLD"

        review_action = approval_handler.get_action(review_id)
        assert review_action is not None
        assert review_action.mode == "REVIEW"

    def test_get_nonexistent_action(self, approval_handler):
        """Test getting non-existent action."""
        action = approval_handler.get_action("nonexistent")
        assert action is None

    def test_hold_and_review_queues_separate(self, approval_handler):
        """Test HOLD and REVIEW queues are separate."""
        hold_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})
        review_id = approval_handler.queue_review("update", "config", "Update", {})

        hold_items = approval_handler.get_hold_queue()
        review_items = approval_handler.get_review_queue()

        assert len(hold_items) == 1
        assert len(review_items) == 1
        assert hold_items[0].action_id == hold_id
        assert review_items[0].action_id == review_id

    def test_multiple_items(self, approval_handler):
        """Test multiple items in queue."""
        id1 = approval_handler.queue_hold("deploy", "prod", "Deploy 1", {})
        id2 = approval_handler.queue_hold("deploy", "staging", "Deploy 2", {})
        id3 = approval_handler.queue_hold("restart", "service", "Restart", {})

        items = approval_handler.get_hold_queue()
        assert len(items) == 3

        # Release one
        executed = []
        approval_handler.handle_hold_release(id2, lambda: executed.append(True))

        items = approval_handler.get_hold_queue()
        assert len(items) == 2
        remaining_ids = {item.action_id for item in items}
        assert id1 in remaining_ids
        assert id3 in remaining_ids
        assert id2 not in remaining_ids

    def test_item_metadata_preserved(self, approval_handler):
        """Test item metadata is preserved."""
        metadata = {"version": "1.0", "author": "test"}
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", metadata)

        action = approval_handler.get_action(action_id)
        assert action.context == metadata

    def test_item_timestamp(self, approval_handler):
        """Test items have timestamps."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        action = approval_handler.get_action(action_id)
        assert action.timestamp is not None
        assert len(action.timestamp) > 0

    # === Additional tests for missing coverage ===

    def test_log_auto(self, approval_handler):
        """Test log_auto method."""
        approval_handler.log_auto("deploy", "production", "Deploy v1.2.3")

        # Check decisions.log was written
        decisions_log = approval_handler._decisions_log
        assert decisions_log.exists()
        content = decisions_log.read_text()
        assert "deploy" in content
        assert "production" in content
        assert "auto_executed" in content

    def test_handle_approve_action_not_found(self, approval_handler):
        """Test handle_approve with non-existent action in either queue."""
        result = approval_handler.handle_approve("nonexistent", lambda: None)
        assert result is False

    def test_handle_approve_exception(self, approval_handler):
        """Test handle_approve when send_fn raises exception."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        def failing_send():
            raise RuntimeError("Send failed")

        result = approval_handler.handle_approve(action_id, failing_send)

        assert result is False
        # Check decisions.log has execution_failed
        content = approval_handler._decisions_log.read_text()
        assert "execution_failed" in content

    def test_handle_edit_review(self, approval_handler):
        """Test handle_edit for REVIEW item."""
        action_id = approval_handler.queue_review("update", "config", "Original", {})

        sent = []
        def send_fn():
            sent.append(True)

        result = approval_handler.handle_edit(action_id, "Edited content", send_fn)

        assert result is True
        assert len(sent) == 1

        # Check decisions.log
        content = approval_handler._decisions_log.read_text()
        assert "edited_and_sent" in content
        assert "Original" in content

    def test_handle_edit_hold(self, approval_handler):
        """Test handle_edit for HOLD item."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Original", {})

        sent = []
        def send_fn():
            sent.append(True)

        result = approval_handler.handle_edit(action_id, "Edited", send_fn)

        assert result is True
        assert len(sent) == 1

    def test_handle_edit_not_found(self, approval_handler):
        """Test handle_edit with non-existent action."""
        result = approval_handler.handle_edit("nonexistent", "Edited", lambda: None)
        assert result is False

    def test_handle_edit_exception(self, approval_handler):
        """Test handle_edit when send_fn raises exception."""
        action_id = approval_handler.queue_review("update", "config", "Original", {})

        def failing_send():
            raise RuntimeError("Send failed")

        result = approval_handler.handle_edit(action_id, "Edited", failing_send)

        assert result is False
        content = approval_handler._decisions_log.read_text()
        assert "execution_failed" in content

    def test_handle_block_hold_item(self, approval_handler):
        """Test handle_block for HOLD item (not just REVIEW)."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        result = approval_handler.handle_block(action_id, "Not needed")

        assert result is True
        hold_items = approval_handler.get_hold_queue()
        assert len(hold_items) == 0

        content = approval_handler._decisions_log.read_text()
        assert "blocked: Not needed" in content

    def test_handle_block_not_found(self, approval_handler):
        """Test handle_block with non-existent action."""
        result = approval_handler.handle_block("nonexistent", "reason")
        assert result is False

    def test_handle_block_welcome_message(self, approval_handler):
        """Test handle_block logs inquiry declined for welcome_message."""
        action_id = approval_handler.queue_review("welcome_message", "inquiry-123", "Welcome", {})

        result = approval_handler.handle_block(action_id, "Spam")

        assert result is True
        # Check declined.json was created
        declined_file = approval_handler._fs_base / "prospects" / "inquiry-123" / "declined.json"
        assert declined_file.exists()
        data = json.loads(declined_file.read_text())
        assert data["inquiry_id"] == "inquiry-123"
        assert data["reason"] == "Spam"

    def test_handle_hold_release_not_found(self, approval_handler):
        """Test handle_hold_release with non-existent action."""
        result = approval_handler.handle_hold_release("nonexistent", lambda: None)
        assert result is False

    def test_handle_hold_release_exception(self, approval_handler):
        """Test handle_hold_release when execute_fn raises exception."""
        action_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        def failing_execute():
            raise RuntimeError("Deploy failed")

        result = approval_handler.handle_hold_release(action_id, failing_execute)

        assert result is False
        content = approval_handler._decisions_log.read_text()
        assert "execution_failed" in content

    def test_add_urgency_flag_review_48h(self, approval_handler):
        """Test add_urgency_flag for REVIEW at 48 hours."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        result = approval_handler.add_urgency_flag(action_id, 48)

        assert result is True
        action = approval_handler.get_action(action_id)
        assert action.urgency_flag == "Response window closing"
        assert action.hours_waiting == 48.0

    def test_add_urgency_flag_review_24h(self, approval_handler):
        """Test add_urgency_flag for REVIEW at 24 hours."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        result = approval_handler.add_urgency_flag(action_id, 24)

        assert result is True
        action = approval_handler.get_action(action_id)
        assert action.urgency_flag == "No decision in 24h — client may disengage"
        assert action.hours_waiting == 24.0

    def test_add_urgency_flag_below_24h(self, approval_handler):
        """Test add_urgency_flag below 24 hours doesn't set flag."""
        action_id = approval_handler.queue_review("update", "config", "Update", {})

        result = approval_handler.add_urgency_flag(action_id, 12)

        assert result is True
        action = approval_handler.get_action(action_id)
        assert action.urgency_flag is None
        assert action.hours_waiting == 12.0

    def test_log_inquiry_declined(self, approval_handler):
        """Test _log_inquiry_declined internal method."""
        approval_handler._log_inquiry_declined("inquiry-456", "Blocked by operator")

        declined_file = approval_handler._fs_base / "prospects" / "inquiry-456" / "declined.json"
        assert declined_file.exists()
        data = json.loads(declined_file.read_text())
        assert data["inquiry_id"] == "inquiry-456"
        assert data["reason"] == "Blocked by operator"

    def test_get_review_queue_corrupt_json(self, approval_handler, tmp_path):
        """Test get_review_queue handles corrupt JSON."""
        # Create corrupt JSON file
        corrupt_file = approval_handler._review_queue_dir / "corrupt.json"
        corrupt_file.write_text("{ invalid json")

        items = approval_handler.get_review_queue()
        assert items == []  # Should skip corrupt file

    def test_get_hold_queue_corrupt_json(self, approval_handler):
        """Test get_hold_queue handles corrupt JSON."""
        corrupt_file = approval_handler._hold_queue_dir / "corrupt.json"
        corrupt_file.write_text("{ invalid json")

        items = approval_handler.get_hold_queue()
        assert items == []  # Should skip corrupt file

    def test_read_action_corrupt_json(self, approval_handler):
        """Test _read_action handles corrupt JSON."""
        corrupt_file = approval_handler._review_queue_dir / "corrupt.json"
        corrupt_file.write_text("{ invalid json")

        action = approval_handler._read_action("corrupt", approval_handler._review_queue_dir)
        assert action is None

    def test_decisions_log_created_on_init(self, tmp_path):
        """Test decisions.log is created on handler initialization."""
        handler = OpsApprovalHandler(tmp_path / "test_ops")

        assert handler._decisions_log.exists()
        assert handler._decisions_log.is_file()

    def test_write_action_creates_file(self, approval_handler):
        """Test _write_action creates proper JSON file."""
        action = OpsApprovalAction(
            action_id="test-123",
            action_type="deploy",
            entity_id="prod",
            mode="HOLD",
            content="Deploy",
            context={},
            timestamp="2024-01-01T00:00:00Z"
        )

        approval_handler._write_action(action, approval_handler._hold_queue_dir)

        action_file = approval_handler._hold_queue_dir / "test-123.json"
        assert action_file.exists()
        data = json.loads(action_file.read_text())
        assert data["action_id"] == "test-123"
