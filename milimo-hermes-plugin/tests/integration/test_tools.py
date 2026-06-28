"""Integration tests for Hermes plugin tools (milimo_status, warroom, approve, veto)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from milimo_core.ops.approval_handler import OpsApprovalHandler
from milimo_core.cost_guard import CostGuard, CostGuardConfig
from milimo_core.milimo_paths import MILIMO_DIR
from milimo_core.notifications import WarRoomNotifier, SlackConfig, TelegramConfig

from milimo_hermes_plugin.tools import (
    set_claw_launcher,
    set_approval_handler,
    set_cost_guard,
    set_warroom_notifier,
    handle_milimo_status,
    handle_milimo_warroom,
    handle_milimo_approve,
    handle_milimo_veto,
    handle_delegate_task,
)


@pytest.fixture
def temp_milimo_dir(tmp_path):
    """Create temporary Milimo directory for testing."""
    milimo_dir = tmp_path / "test_milimo"
    milimo_dir.mkdir(parents=True)
    return milimo_dir


@pytest.fixture
def approval_handler(temp_milimo_dir):
    """Create OpsApprovalHandler for testing."""
    return OpsApprovalHandler(temp_milimo_dir)


@pytest.fixture
def cost_guard():
    """Create CostGuard for testing."""
    config = CostGuardConfig(daily_token_limit=50000, warning_threshold_percent=60.0, alert_threshold_percent=80.0)
    return CostGuard(config)


@pytest.fixture
def warroom_notifier():
    """Create WarRoomNotifier for testing."""
    return WarRoomNotifier(
        slack_config=SlackConfig(webhook_url="https://hooks.slack.com/test"),
        telegram_config=TelegramConfig(bot_token="123:test")
    )


@pytest.fixture
def mock_claw_launcher():
    """Create mock claw launcher."""
    launcher = MagicMock()
    launcher.status.return_value = {
        "running": True,
        "launcher_pid": 12345,
        "timestamp": "2024-01-01T00:00:00Z",
        "claws": {
            "build": {"status": "ready", "last_activity": "2024-01-01T00:00:00Z"},
            "content": {"status": "busy", "last_activity": "2024-01-01T00:00:00Z"},
            "ops": {"status": "ready", "last_activity": "2024-01-01T00:00:00Z"},
            "analytics": {"status": "ready", "last_activity": "2024-01-01T00:00:00Z"},
            "finance": {"status": "ready", "last_activity": "2024-01-01T00:00:00Z"},
            "assistant": {"status": "ready", "last_activity": "2024-01-01T00:00:00Z"},
        }
    }
    return launcher


class TestMilimoStatusIntegration:
    """Integration tests for milimo_status tool."""

    @pytest.mark.asyncio
    async def test_status_returns_all_six_claws(self, mock_claw_launcher):
        """Test status returns all 6 claws."""
        set_claw_launcher(mock_claw_launcher)

        ctx = MagicMock()
        result = await handle_milimo_status(ctx, detailed=True)

        assert "claws" in result
        claws = result["claws"]
        assert len(claws) == 6
        assert all(claw in claws for claw in ["build", "content", "ops", "analytics", "finance", "assistant"])

    @pytest.mark.asyncio
    async def test_status_detailed_includes_launcher_info(self, mock_claw_launcher):
        """Test detailed status includes launcher PID and timestamp."""
        set_claw_launcher(mock_claw_launcher)

        ctx = MagicMock()
        result = await handle_milimo_status(ctx, detailed=True)

        assert result["launcher_pid"] == 12345
        assert result["timestamp"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_status_simplified_mode(self, mock_claw_launcher):
        """Test simplified status mode."""
        set_claw_launcher(mock_claw_launcher)

        ctx = MagicMock()
        result = await handle_milimo_status(ctx, detailed=False)

        assert result["status"] == "operational"
        assert "claws" in result

    @pytest.mark.asyncio
    async def test_status_without_launcher_fallback(self):
        """Test fallback when no launcher set."""
        import milimo_hermes_plugin.tools as tools_module
        original = tools_module._claw_launcher
        tools_module._claw_launcher = None

        try:
            ctx = MagicMock()
            result = await handle_milimo_status(ctx, detailed=False)

            assert result["status"] == "operational"
            assert "claws" in result
        finally:
            tools_module._claw_launcher = original


class TestMilimoWarroomIntegration:
    """Integration tests for milimo_warroom tool."""

    @pytest.mark.asyncio
    async def test_warroom_hold_queue_shows_both_queues(self, approval_handler, warroom_notifier):
        """Test hold_queue action shows both HOLD and REVIEW queues."""
        set_approval_handler(approval_handler)
        set_warroom_notifier(warroom_notifier)

        # Add items
        approval_handler.queue_hold("deploy", "production", "Deploy v1.0", {"version": "1.0"})
        approval_handler.queue_review("config", "stripe", "Update keys", {"keys": ["sk_test"]})

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="hold_queue")

        assert result["total_hold"] == 1
        assert result["total_review"] == 1
        assert len(result["hold_queue"]) == 1
        assert len(result["review_queue"]) == 1

    @pytest.mark.asyncio
    async def test_warroom_cost_guard_returns_usage(self, cost_guard, warroom_notifier):
        """Test cost_guard action returns usage data."""
        set_cost_guard(cost_guard)
        set_warroom_notifier(warroom_notifier)

        # Record some usage
        cost_guard.record_inference("build", 1000)
        cost_guard.record_inference("content", 2000)

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="cost_guard")

        assert "summary" in result
        assert result["summary"]["total_tokens"] == 3000
        assert "by_role" in result

    @pytest.mark.asyncio
    async def test_warroom_approve_flow(self, approval_handler):
        """Test approve flow through warroom."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_review("update", "config", "Update config", {})

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="approve", item_id=item_id)

        assert result["action"] == "approve"
        assert result["item_id"] == item_id
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_warroom_veto_flow(self, approval_handler):
        """Test veto flow through warroom."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="veto", item_id=item_id, reason="Not ready")

        assert result["action"] == "veto"
        assert result["item_id"] == item_id
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_warroom_approve_nonexistent(self, approval_handler):
        """Test approve non-existent item."""
        set_approval_handler(approval_handler)

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="approve", item_id="nonexistent")

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_warroom_approve_missing_item_id(self, approval_handler):
        """Test approve without item_id."""
        set_approval_handler(approval_handler)

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="approve")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_warroom_veto_missing_reason(self, approval_handler):
        """Test veto without reason (should use default)."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        ctx = MagicMock()
        result = await handle_milimo_warroom(ctx, action="veto", item_id=item_id)

        assert result["status"] == "rejected"


class TestMilimoApproveIntegration:
    """Integration tests for milimo_approve tool."""

    @pytest.mark.asyncio
    async def test_approve_with_delegation(self, approval_handler):
        """Test approve with delegation to claw."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_review("update", "config", "Update config", {})

        # Mock the delegation
        with patch("milimo_hermes_plugin.delegation.HermesDelegateAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_result = MagicMock()
            mock_result.claw = "ops"
            mock_result.output = "Task completed"
            mock_result.success = True
            mock_result.error = None
            mock_adapter.delegate.return_value = [mock_result]
            mock_adapter_class.return_value = mock_adapter

            ctx = MagicMock()
            result = await handle_milimo_approve(
                ctx,
                item_id=item_id,
                reason="Approved by operator",
                delegate_to_claw="ops",
                delegation_goal="Execute config update"
            )

            assert result["status"] == "approved"
            assert result["delegated_to"] == "ops"
            assert result["delegation_result"]["claw"] == "ops"
            assert result["delegation_result"]["success"] is True

    @pytest.mark.asyncio
    async def test_approve_without_delegation(self, approval_handler):
        """Test approve without delegation."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_review("update", "config", "Update config", {})

        ctx = MagicMock()
        result = await handle_milimo_approve(
            ctx,
            item_id=item_id,
            reason="Approved"
        )

        assert result["status"] == "approved"
        assert "delegated_to" not in result

    @pytest.mark.asyncio
    async def test_approve_not_found(self, approval_handler):
        """Test approve non-existent item."""
        set_approval_handler(approval_handler)

        ctx = MagicMock()
        result = await handle_milimo_approve(
            ctx,
            item_id="nonexistent",
            reason="Test"
        )

        assert result["status"] == "failed"
        assert "not found" in result.get("error", "").lower()


class TestMilimoVetoIntegration:
    """Integration tests for milimo_veto tool."""

    @pytest.mark.asyncio
    async def test_veto_hold_item(self, approval_handler):
        """Test veto on HOLD queue item."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_hold("deploy", "prod", "Deploy", {})

        ctx = MagicMock()
        result = await handle_milimo_veto(ctx, item_id=item_id, reason="Failed tests")

        assert result["action"] == "veto"
        assert result["status"] == "rejected"
        assert result["reason"] == "Failed tests"

    @pytest.mark.asyncio
    async def test_veto_review_item(self, approval_handler):
        """Test veto on REVIEW queue item."""
        set_approval_handler(approval_handler)

        item_id = approval_handler.queue_review("update", "config", "Update", {})

        ctx = MagicMock()
        result = await handle_milimo_veto(ctx, item_id=item_id, reason="Invalid config")

        assert result["status"] == "rejected"


class TestDelegateTaskIntegration:
    """Integration tests for delegate_task tool."""

    @pytest.mark.asyncio
    async def test_delegate_multiple_tasks(self):
        """Test delegating multiple tasks."""
        with patch("milimo_hermes_plugin.delegation.HermesDelegateAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_results = []
            for claw in ["build", "content", "ops"]:
                mock_result = MagicMock()
                mock_result.claw = claw
                mock_result.output = f"{claw} completed"
                mock_result.success = True
                mock_result.error = None
                mock_results.append(mock_result)
            mock_adapter.delegate.return_value = mock_results
            mock_adapter_class.return_value = mock_adapter

            ctx = MagicMock()
            result = await handle_delegate_task(ctx, tasks=[
                {"claw": "build", "goal": "Build app", "context": "", "priority": 1},
                {"claw": "content", "goal": "Write content", "context": "", "priority": 0},
                {"claw": "ops", "goal": "Deploy", "context": "", "priority": 2},
            ])

            assert len(result) == 3
            assert all(r["success"] for r in result)
            assert result[0]["claw"] == "build"
            assert result[1]["claw"] == "content"
            assert result[2]["claw"] == "ops"

    @pytest.mark.asyncio
    async def test_delegate_single_task(self):
        """Test delegating single task."""
        with patch("milimo_hermes_plugin.delegation.HermesDelegateAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_result = MagicMock()
            mock_result.claw = "analytics"
            mock_result.output = "Analysis complete"
            mock_result.success = True
            mock_result.error = None
            mock_adapter.delegate.return_value = [mock_result]
            mock_adapter_class.return_value = mock_adapter

            ctx = MagicMock()
            result = await handle_delegate_task(ctx, tasks=[
                {"claw": "analytics", "goal": "Analyze metrics", "priority": 1}
            ])

            assert len(result) == 1
            assert result[0]["claw"] == "analytics"
            assert result[0]["success"] is True

    @pytest.mark.asyncio
    async def test_delegate_with_context(self):
        """Test delegation with context passed through."""
        with patch("milimo_hermes_plugin.delegation.HermesDelegateAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_result = MagicMock()
            mock_result.claw = "finance"
            mock_result.output = "Processed"
            mock_result.success = True
            mock_result.error = None
            mock_adapter.delegate.return_value = [mock_result]
            mock_adapter_class.return_value = mock_adapter

            ctx = MagicMock()
            await handle_delegate_task(ctx, tasks=[
                {"claw": "finance", "goal": "Process payment", "context": "User requested refund", "priority": 1}
            ])

            # Verify the task was passed with context
            call_args = mock_adapter.delegate.call_args[0][0]
            assert call_args[0].claw == "finance"
            assert call_args[0].context == "User requested refund"
