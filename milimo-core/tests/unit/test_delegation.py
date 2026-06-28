"""Unit tests for delegation protocol."""

import pytest
from milimo_core.protocols.delegation import ClawTask, ClawResult, DelegationAdapter


class TestClawTask:
    """Tests for ClawTask dataclass."""

    def test_claw_task_creation(self):
        """Test creating a ClawTask with all fields."""
        task = ClawTask(
            claw="content",
            goal="Write a blog post",
            context="Topic: AI",
            priority=5,
        )
        assert task.claw == "content"
        assert task.goal == "Write a blog post"
        assert task.context == "Topic: AI"
        assert task.priority == 5

    def test_claw_task_defaults(self):
        """Test ClawTask with default values."""
        task = ClawTask(claw="build", goal="Fix bug")
        assert task.claw == "build"
        assert task.goal == "Fix bug"
        assert task.context == ""
        assert task.priority == 0

    def test_claw_task_priority_validation(self):
        """Test priority bounds."""
        task = ClawTask(claw="ops", goal="Deploy", priority=10)
        assert task.priority == 10

        task_low = ClawTask(claw="ops", goal="Deploy", priority=-5)
        assert task_low.priority == -5


class TestClawResult:
    """Tests for ClawResult dataclass."""

    def test_claw_result_success(self):
        """Test successful ClawResult."""
        result = ClawResult(
            claw="content",
            output="Blog post content",
            success=True,
            error=None,
        )
        assert result.claw == "content"
        assert result.output == "Blog post content"
        assert result.success is True
        assert result.error is None

    def test_claw_result_failure(self):
        """Test failed ClawResult."""
        result = ClawResult(
            claw="analytics",
            output="",
            success=False,
            error="API rate limit exceeded",
        )
        assert result.claw == "analytics"
        assert result.success is False
        assert result.error == "API rate limit exceeded"

    def test_claw_result_defaults(self):
        """Test ClawResult with minimal fields."""
        result = ClawResult(claw="finance", output="Report", success=True)
        assert result.claw == "finance"
        assert result.output == "Report"
        assert result.success is True
        assert result.error is None


class TestDelegationAdapter:
    """Tests for DelegationAdapter abstract base class."""

    def test_delegation_adapter_is_abstract(self):
        """Test that DelegationAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DelegationAdapter()

    def test_claw_toolsets_structure(self):
        """Test CLAW_TOOLSETS has expected structure."""
        assert isinstance(DelegationAdapter.CLAW_TOOLSETS, dict)
        expected_claws = {"build", "content", "ops", "analytics", "finance", "assistant"}
        assert set(DelegationAdapter.CLAW_TOOLSETS.keys()) == expected_claws

        for claw, tools in DelegationAdapter.CLAW_TOOLSETS.items():
            assert isinstance(tools, list)
            assert len(tools) > 0
            for tool in tools:
                assert isinstance(tool, str)

    def test_claw_contexts_structure(self):
        """Test CLAW_CONTEXTS has expected structure."""
        assert isinstance(DelegationAdapter.CLAW_CONTEXTS, dict)
        expected_claws = {"build", "content", "ops", "analytics", "finance", "assistant"}
        assert set(DelegationAdapter.CLAW_CONTEXTS.keys()) == expected_claws

        for claw, context in DelegationAdapter.CLAW_CONTEXTS.items():
            assert isinstance(context, str)
            assert len(context) > 0

    def test_toolsets_per_claw(self):
        """Test specific toolsets for each claw."""
        assert "file" in DelegationAdapter.CLAW_TOOLSETS["build"]
        assert "shell" in DelegationAdapter.CLAW_TOOLSETS["build"]
        assert "web" in DelegationAdapter.CLAW_TOOLSETS["content"]
        assert "file" in DelegationAdapter.CLAW_TOOLSETS["ops"]
        assert "file" in DelegationAdapter.CLAW_TOOLSETS["analytics"]
        assert "file" in DelegationAdapter.CLAW_TOOLSETS["finance"]
        assert "file" in DelegationAdapter.CLAW_TOOLSETS["assistant"]
        assert "web" in DelegationAdapter.CLAW_TOOLSETS["assistant"]


class TestDelegationAdapterImplementation:
    """Tests for DelegationAdapter implementations."""

    @pytest.mark.asyncio
    async def test_mock_delegation_adapter(self, mock_delegation_adapter, sample_claw_task):
        """Test mock delegation adapter works correctly."""
        result = await mock_delegation_adapter.delegate_single(sample_claw_task)

        assert result.claw == "content"
        assert result.success is True
        mock_delegation_adapter.delegate_single.assert_called_once_with(sample_claw_task)

    @pytest.mark.asyncio
    async def test_mock_delegation_adapter_batch(self, mock_delegation_adapter, sample_claw_task):
        """Test mock delegation adapter batch delegation."""
        tasks = [sample_claw_task, sample_claw_task]
        results = await mock_delegation_adapter.delegate(tasks)

        assert len(results) == 2
        assert all(r.success for r in results)
        mock_delegation_adapter.delegate.assert_called_once_with(tasks)

    def test_build_context(self):
        """Test DelegationAdapter.build_context method."""
        # Create a minimal implementation for testing
        class TestAdapter(DelegationAdapter):
            async def delegate(self, tasks):
                return []
            async def delegate_single(self, task):
                return ClawResult(claw=task.claw, output="test", success=True)

        adapter = TestAdapter()
        task = ClawTask(claw="content", goal="Write", context="AI topic")
        context = adapter.build_context(task)

        assert "Content Claw" in context
        assert "AI topic" in context

    def test_build_context_no_context(self):
        """Test build_context with empty context."""
        class TestAdapter(DelegationAdapter):
            async def delegate(self, tasks):
                return []
            async def delegate_single(self, task):
                return ClawResult(claw=task.claw, output="test", success=True)

        adapter = TestAdapter()
        task = ClawTask(claw="build", goal="Build")
        context = adapter.build_context(task)

        assert "Build Claw" in context
        assert context == "You are the Build Claw. Handle CI/CD, deployments, dependency auditing."
