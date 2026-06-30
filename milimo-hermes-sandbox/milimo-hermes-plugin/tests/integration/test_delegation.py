"""Integration tests for Hermes plugin delegation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from milimo_core.protocols.delegation import ClawTask, ClawResult, DelegationAdapter
from milimo_hermes_plugin.delegation import HermesDelegateAdapter


class TestHermesDelegateAdapter:
    """Test HermesDelegateAdapter."""

    def test_adapter_implements_interface(self):
        """Test HermesDelegateAdapter implements DelegationAdapter."""
        adapter = HermesDelegateAdapter()
        assert isinstance(adapter, DelegationAdapter)

    def test_claw_toolsets_mapping(self):
        """Test CLAW_TOOLSETS mapping exists for all 6 claws."""
        adapter = HermesDelegateAdapter()

        expected_claws = ["build", "content", "ops", "analytics", "finance", "assistant"]
        for claw in expected_claws:
            assert claw in adapter.CLAW_TOOLSETS
            assert isinstance(adapter.CLAW_TOOLSETS[claw], list)
            assert len(adapter.CLAW_TOOLSETS[claw]) > 0

    def test_build_context(self):
        """Test context building for tasks."""
        adapter = HermesDelegateAdapter()

        task = ClawTask(
            claw="content",
            goal="Generate blog post about AI",
            context="User requested technical blog post",
            priority=1
        )

        context = adapter.build_context(task)

        assert "Content Claw" in context
        assert "User requested technical blog post" in context

    def test_build_context_empty_context(self):
        """Test context building with empty context."""
        adapter = HermesDelegateAdapter()

        task = ClawTask(
            claw="analytics",
            goal="Analyze metrics",
            context="",
            priority=0
        )

        context = adapter.build_context(task)

        assert "Analytics Claw" in context

    @pytest.mark.asyncio
    async def test_delegate_single(self):
        """Test delegate_single method."""
        adapter = HermesDelegateAdapter()

        # Mock _invoke_delegate_task
        with patch.object(adapter, '_invoke_delegate_task', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["Task completed successfully"]

            task = ClawTask(
                claw="build",
                goal="Build new feature",
                context="",
                priority=1
            )

            result = await adapter.delegate_single(task)

            assert isinstance(result, ClawResult)
            assert result.claw == "build"
            assert result.output == "Task completed successfully"
            assert result.success is True

    @pytest.mark.asyncio
    async def test_delegate_single_error_result(self):
        """Test delegate_single with error result."""
        adapter = HermesDelegateAdapter()

        with patch.object(adapter, '_invoke_delegate_task', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = [{"error": "Task failed"}]

            task = ClawTask(
                claw="finance",
                goal="Process payment",
                context="",
                priority=1
            )

            result = await adapter.delegate_single(task)

            assert result.success is False
            assert result.error == "Task failed"

    @pytest.mark.asyncio
    async def test_delegate_multiple(self):
        """Test delegate with multiple tasks."""
        adapter = HermesDelegateAdapter()

        with patch.object(adapter, '_invoke_delegate_task', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["Result 1", "Result 2", "Result 3"]

            tasks = [
                ClawTask(claw="build", goal="Task 1", context="", priority=1),
                ClawTask(claw="content", goal="Task 2", context="", priority=0),
                ClawTask(claw="ops", goal="Task 3", context="", priority=2),
            ]

            results = await adapter.delegate(tasks)

            assert len(results) == 3
            assert results[0].claw == "build"
            assert results[1].claw == "content"
            assert results[2].claw == "ops"

    @pytest.mark.asyncio
    async def test_delegate_empty_list(self):
        """Test delegate with empty list."""
        adapter = HermesDelegateAdapter()

        results = await adapter.delegate([])

        assert results == []

    @pytest.mark.asyncio
    async def test_delegate_matches_input_order(self):
        """Test results match input task order."""
        adapter = HermesDelegateAdapter()

        with patch.object(adapter, '_invoke_delegate_task', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = ["A", "B", "C"]

            tasks = [
                ClawTask(claw="build", goal="Build", context="", priority=1),
                ClawTask(claw="analytics", goal="Analyze", context="", priority=0),
                ClawTask(claw="finance", goal="Finance", context="", priority=2),
            ]

            results = await adapter.delegate(tasks)

            assert results[0].claw == "build"
            assert results[1].claw == "analytics"
            assert results[2].claw == "finance"

    def test_claw_toolsets_content(self):
        """Test specific toolsets for content claw."""
        adapter = HermesDelegateAdapter()

        content_toolsets = adapter.CLAW_TOOLSETS["content"]
        assert "web" in content_toolsets
        assert "file" in content_toolsets

    def test_claw_toolsets_finance(self):
        """Test specific toolsets for finance claw."""
        adapter = HermesDelegateAdapter()

        finance_toolsets = adapter.CLAW_TOOLSETS["finance"]
        assert "file" in finance_toolsets

    def test_claw_toolsets_build(self):
        """Test specific toolsets for build claw."""
        adapter = HermesDelegateAdapter()

        build_toolsets = adapter.CLAW_TOOLSETS["build"]
        assert "shell" in build_toolsets
        assert "file" in build_toolsets

    @pytest.mark.asyncio
    async def test_invoke_delegate_task_raises_not_implemented(self):
        """Test _invoke_delegate_task raises NotImplementedError by default."""
        adapter = HermesDelegateAdapter()

        with pytest.raises(NotImplementedError):
            await adapter._invoke_delegate_task([{"goal": "test", "toolsets": ["file"], "context": ""}])


class MockHermesDelegateAdapter(HermesDelegateAdapter):
    """Mock adapter for testing with simulated delegate_task."""

    def __init__(self, mock_results=None):
        super().__init__()
        self._mock_results = mock_results or []
        self._call_count = 0

    async def _invoke_delegate_task(self, tasks):
        self._call_count += 1
        if self._mock_results:
            return self._mock_results.pop(0)
        return [f"Mock result {i}" for i in range(len(tasks))]


class TestHermesDelegateAdapterWithMock:
    """Test HermesDelegateAdapter with mocked delegate_task."""

    @pytest.mark.asyncio
    async def test_mock_adapter_delegate(self):
        """Test mock adapter delegation."""
        adapter = MockHermesDelegateAdapter([["Result 1", "Result 2"]])

        tasks = [
            ClawTask(claw="build", goal="Build", context="", priority=1),
            ClawTask(claw="content", goal="Content", context="", priority=0),
        ]

        results = await adapter.delegate(tasks)

        assert len(results) == 2
        assert results[0].output == "Result 1"
        assert results[1].output == "Result 2"

    @pytest.mark.asyncio
    async def test_mock_adapter_multiple_calls(self):
        """Test mock adapter with multiple calls."""
        adapter = MockHermesDelegateAdapter([
            ["First call result"],
            ["Second call result"],
        ])

        # First call
        r1 = await adapter.delegate([ClawTask(claw="build", goal="1", context="", priority=1)])
        # Second call
        r2 = await adapter.delegate([ClawTask(claw="content", goal="2", context="", priority=1)])

        assert r1[0].output == "First call result"
        assert r2[0].output == "Second call result"
        assert adapter._call_count == 2
