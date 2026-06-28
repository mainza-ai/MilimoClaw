"""Shared test configuration and fixtures for milimo-core."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from milimo_core.milimo_paths import (
    MILIMO_DIR, CLAWS_DIR, claw_base, config_path, mesh_dir,
    health_dir, tools_dir, logs_dir, marketplace_dir, latency_dir,
    cohorts_dir, attestations_dir, analytics_dir, inference_dir,
    events_dir, sandboxes_dir
)
from milimo_core.tool_registry import ToolRegistry
from milimo_core.privacy_router import PrivacyRouter
from milimo_core.inference_client import NvidiaInferenceClient as InferenceClient
from milimo_core.service_factory import (
    create_github_client, create_vercel_client, create_sentry_client,
    create_stripe_client, create_railway_client, log_active_services
)
from milimo_core.provenance_signer import ProvenanceSigner
from milimo_core.tool_generator import ToolGenerator
from milimo_core.tool_validator import ToolValidator
from milimo_core.tool_sandbox import ToolSandbox
from milimo_core.protocols.delegation import ClawTask, ClawResult, DelegationAdapter
from milimo_core.protocols.scheduling import ScheduledJob, SchedulerInterface
from milimo_core.evolution_scheduler import EvolutionScheduler, EvolutionSchedulerConfig
from milimo_core.cost_guard import CostGuard, CostGuardConfig
from milimo_core.ssrf_validator import SSRFValidator, SSRFPolicy
from milimo_core.notifications import WarRoomNotifier, SlackConfig, TelegramConfig, NotificationPayload
from milimo_core.ops.approval_handler import OpsApprovalHandler


class MockMilimoPaths:
    """Mock MilimoPaths for testing with temp directories."""

    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.claws = base_dir / "claws"
        self.ops = base_dir / "claws" / "ops"
        self.logs = base_dir / "claws" / "logs"
        self.data = base_dir / "claws" / "data"
        self.tools = base_dir / "claws" / "tools"
        self.config = base_dir / "claws" / "config"

        # Create directories
        self.claws.mkdir(parents=True, exist_ok=True)
        self.ops.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.data.mkdir(parents=True, exist_ok=True)
        self.tools.mkdir(parents=True, exist_ok=True)
        self.config.mkdir(parents=True, exist_ok=True)

    def claw_path(self, role: str) -> Path:
        return self.claws / role

    def claw_drafts_path(self, role: str) -> Path:
        return self.claws / role / "drafts"

    def claw_reports_path(self, role: str) -> Path:
        return self.claws / role / "reports"

    def claw_invoices_path(self, role: str) -> Path:
        return self.claws / role / "invoices"

    def ops_approval_path(self) -> Path:
        return self.ops / "approval"

    def ops_hold_queue_path(self) -> Path:
        return self.ops / "approval" / "hold"

    def ops_review_queue_path(self) -> Path:
        return self.ops / "approval" / "review"

    def tool_registry_path(self) -> Path:
        return self.tools / "registry.json"

    def tool_sandbox_path(self, tool_name: str) -> Path:
        return self.tools / "sandbox" / tool_name

    def config_path(self, filename: str) -> Path:
        return self.config / filename

    def log_path(self, filename: str) -> Path:
        return self.logs / filename


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_milimo_paths(temp_dir):
    """Create a mock MilimoPaths instance with temp directories."""
    return MockMilimoPaths(temp_dir)


@pytest.fixture
def mock_tool_registry():
    """Create a ToolRegistry instance."""
    return ToolRegistry()


@pytest.fixture
def mock_privacy_router():
    """Create a PrivacyRouter instance."""
    return PrivacyRouter()


@pytest.fixture
def mock_inference_client():
    """Create a mock InferenceClient."""
    client = MagicMock(spec=InferenceClient)
    client.complete = AsyncMock(return_value={"content": "mock response", "usage": {"total_tokens": 100}})
    client.stream = AsyncMock()
    return client


@pytest.fixture
def mock_service_factory():
    """Create a mock ServiceFactory."""
    factory = MagicMock(spec=ServiceFactory)
    factory.create_service = MagicMock()
    return factory


@pytest.fixture
def mock_provenance_signer():
    """Create a mock ProvenanceSigner."""
    signer = MagicMock(spec=ProvenanceSigner)
    signer.sign = MagicMock(return_value="mock_signature")
    signer.verify = MagicMock(return_value=True)
    return signer


@pytest.fixture
def mock_tool_generator():
    """Create a mock ToolGenerator."""
    generator = MagicMock(spec=ToolGenerator)
    generator.generate = AsyncMock(return_value="mock_tool_code")
    return generator


@pytest.fixture
def mock_tool_validator():
    """Create a mock ToolValidator."""
    validator = MagicMock(spec=ToolValidator)
    validator.validate = MagicMock(return_value=True)
    return validator


@pytest.fixture
def mock_tool_sandbox():
    """Create a mock ToolSandbox."""
    sandbox = MagicMock(spec=ToolSandbox)
    sandbox.execute = AsyncMock(return_value={"result": "mock_result"})
    return sandbox


@pytest.fixture
def sample_claw_task():
    """Create a sample ClawTask for testing."""
    return ClawTask(
        claw="content",
        goal="Write a blog post",
        context="Topic: AI",
        priority=5,
    )


@pytest.fixture
def sample_claw_result():
    """Create a sample ClawResult for testing."""
    return ClawResult(
        claw="content",
        output="Blog post content",
        success=True,
        error=None,
    )


@pytest.fixture
def mock_delegation_adapter(sample_claw_result):
    """Create a mock DelegationAdapter."""
    adapter = MagicMock(spec=DelegationAdapter)

    async def mock_delegate(tasks):
        return [sample_claw_result] * len(tasks)

    adapter.delegate = AsyncMock(side_effect=mock_delegate)
    adapter.delegate_single = AsyncMock(return_value=sample_claw_result)
    return adapter


@pytest.fixture
def mock_scheduler():
    """Create a mock SchedulerInterface."""
    scheduler = MagicMock(spec=SchedulerInterface)
    scheduler.schedule_job = MagicMock()
    scheduler.unschedule_job = MagicMock()
    scheduler.get_due_jobs = MagicMock(return_value=[])
    scheduler.start = AsyncMock()
    scheduler.stop = AsyncMock()
    return scheduler


@pytest.fixture
def sample_scheduled_job():
    """Create a sample ScheduledJob for testing."""
    return ScheduledJob(
        name="test_job",
        cron_expression="0 * * * *",
        handler="test_handler",
        enabled=True
    )


@pytest.fixture
def evolution_scheduler(mock_milimo_paths):
    """Create an EvolutionScheduler instance."""
    return EvolutionScheduler(fs_base=mock_milimo_paths.ops)


@pytest.fixture
def cost_guard(temp_dir):
    """Create a CostGuard instance with temp metrics directory."""
    config = CostGuardConfig(daily_token_limit=50000)
    metrics_base_dir = temp_dir / "metrics"
    return CostGuard(config=config, metrics_base_dir=metrics_base_dir)


@pytest.fixture
def ssrf_validator():
    """Create an SSRFValidator instance."""
    policy = SSRFPolicy()
    return SSRFValidator(policy)


@pytest.fixture
def slack_config():
    """Create a SlackConfig instance."""
    return SlackConfig(webhook_url="https://hooks.slack.com/test", bot_token="xoxb-test")


@pytest.fixture
def telegram_config():
    """Create a TelegramConfig instance."""
    return TelegramConfig(bot_token="123:test", allowed_ids=[123456])


@pytest.fixture
def notification_payload():
    """Create a sample NotificationPayload."""
    return NotificationPayload(
        title="Test Alert",
        message="This is a test message",
        level="warning",
        metadata={"claw": "content"}
    )


@pytest.fixture
def approval_handler(mock_milimo_paths):
    """Create an OpsApprovalHandler instance."""
    return OpsApprovalHandler(fs_base=mock_milimo_paths.ops)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset CostGuard singleton
    import milimo_core.cost_guard as cg
    cg._cost_guard_instance = None

    # Reset WarRoomNotifier singleton
    import milimo_core.notifications as nf
    nf._warroom_notifier = None

    yield

    # Cleanup
    cg._cost_guard_instance = None
    nf._warroom_notifier = None


# Environment variable fixtures
@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set common environment variables for tests."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NEMOCLAW_POLICY_TIER", "restricted")
    monkeypatch.setenv("NEMOCLAW_SANDBOX_NAME", "test-hermes")
    yield
    # Cleanup handled by monkeypatch


# Async test support
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
