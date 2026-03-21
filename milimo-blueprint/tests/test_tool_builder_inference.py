#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for tool_builder.py - Inference-Based Tool Generation
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from orchestrator.tool_builder import (
    ToolBuilder,
    BuiltTool,
    BuildResult,
    BacktestResult,
)
from orchestrator.tool_proposal import ToolProposal
from orchestrator.pattern_detector import EvolutionPattern


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "war_room": {"operator": "test"},
    "evolution": {
        "min_improvement_percent": 5.0,
    },
}


def create_test_proposal() -> ToolProposal:
    """Create a test tool proposal."""
    pattern = EvolutionPattern(
        pattern_type="high_frequency_action",
        trigger_description="Social post drafts occur frequently",
        metric_target="approval_rate",
        confidence=0.85,
    )

    return ToolProposal(
        tool_name="test_social_optimizer",
        tool_type="optimizer",
        claw_role="content",
        trigger_pattern=pattern,
        metric_target="approval_rate",
        estimated_improvement=12.5,
    )


# ---------------------------------------------------------------------------


class TestToolBuilderInference:
    """Tests for inference-based tool generation in ToolBuilder."""

    @pytest.fixture
    def builder(self, tmp_path: Path) -> ToolBuilder:
        """Create a ToolBuilder instance for testing."""
        return ToolBuilder(
            claw_role="content",
            squad_id="test-squad",
            blueprint_dir=tmp_path,
        )

    def test_initialization(self, builder: ToolBuilder) -> None:
        """Test ToolBuilder initialization."""
        assert builder.claw_role == "content"
        assert builder.squad_id == "test-squad"
        assert builder.min_improvement_percent == 5.0

    def test_validate_syntax_valid(self, builder: ToolBuilder) -> None:
        """Test syntax validation with valid code."""
        valid_code = """
def apply(action_data: dict) -> dict:
    return action_data
"""
        assert builder._validate_syntax(valid_code) is True

    def test_validate_syntax_invalid(self, builder: ToolBuilder) -> None:
        """Test syntax validation with invalid code."""
        invalid_code = """
def apply(action_data: dict
    return action_data
"""
        assert builder._validate_syntax(invalid_code) is False

    def test_generate_skeleton_code(self, builder: ToolBuilder) -> None:
        """Test skeleton code generation."""
        proposal = create_test_proposal()
        code = builder._generate_skeleton_code(proposal)

        assert "test_social_optimizer" in code
        assert "optimizer" in code
        assert "approval_rate" in code
        assert "def apply" in code

    def test_build_inference_prompt(self, builder: ToolBuilder) -> None:
        """Test inference prompt building."""
        proposal = create_test_proposal()
        prompt = builder._build_inference_prompt(proposal)

        assert "# Tool Generation Request" in prompt
        assert "test_social_optimizer" in prompt
        assert "optimizer" in prompt
        assert "content" in prompt
        assert "approval_rate" in prompt
        assert "12.5%" in prompt

    def test_generate_via_inference_no_policy(self, builder: ToolBuilder) -> None:
        """Test inference generation without privacy policy."""
        proposal = create_test_proposal()
        result = builder._generate_via_inference(proposal)

        # Should return None when no privacy policy exists
        assert result is None

    def test_generate_via_inference_with_policy(self, tmp_path: Path) -> None:
        """Test inference generation with privacy policy."""
        # Create privacy policy file
        policy_content = """
policy_version: "0.1.0"
default_backend: local-nim
routes:
  - data_type: source_code
    backend: local-nim
    description: "Source code generation must use local NIM"
"""
        policy_file = tmp_path / "privacy_policy.yaml"
        policy_file.write_text(policy_content)

        builder = ToolBuilder(
            claw_role="content",
            squad_id="test-squad",
            blueprint_dir=tmp_path,
        )

        proposal = create_test_proposal()
        result = builder._generate_via_inference(proposal)

        # Should still return None (no actual NIM endpoint)
        # but should not raise an error
        assert result is None

    def test_generate_tool_code_fallback(self, builder: ToolBuilder) -> None:
        """Test tool code generation fallback to skeleton."""
        proposal = create_test_proposal()
        code = builder._generate_tool_code(proposal)

        # Should fallback to skeleton code
        assert "def apply" in code
        assert proposal.tool_name in code

    def test_check_blocked_imports_requests(self, tmp_path: Path) -> None:
        """Test blocked import detection for requests."""
        from orchestrator.evolution.sandbox_runner import SandboxRunner

        runner = SandboxRunner()
        code = """
import requests

def apply(action_data: dict) -> dict:
    return action_data
"""
        blocked = runner._check_blocked_imports(code)
        assert "requests" in blocked

    def test_check_blocked_imports_subprocess(self, tmp_path: Path) -> None:
        """Test blocked import detection for subprocess."""
        from orchestrator.evolution.sandbox_runner import SandboxRunner

        runner = SandboxRunner()
        code = """
import subprocess

def apply(action_data: dict) -> dict:
    subprocess.run(['ls'])
    return action_data
"""
        blocked = runner._check_blocked_imports(code)
        assert "subprocess" in blocked

    def test_check_blocked_imports_clean(self, tmp_path: Path) -> None:
        """Test no blocked imports in clean code."""
        from orchestrator.evolution.sandbox_runner import SandboxRunner

        runner = SandboxRunner()
        code = """
import json
import math
from datetime import datetime

def apply(action_data: dict) -> dict:
    return action_data
"""
        blocked = runner._check_blocked_imports(code)
        assert len(blocked) == 0


class TestBuildResult:
    """Tests for BuildResult dataclass."""

    def test_default_values(self) -> None:
        """Test BuildResult default values."""
        proposal = create_test_proposal()
        result = BuildResult(proposal=proposal)
        assert result.proposal == proposal
        assert result.tool is None
        assert result.backtest is None
        assert result.passed is False
        assert result.failure_reason == ""

    def test_passed_result(self) -> None:
        """Test passed BuildResult."""
        proposal = create_test_proposal()
        tool = BuiltTool(
            proposal=proposal,
            tool_name="test_tool",
            tool_type="optimizer",
        )
        backtest = BacktestResult(
            tool_name="test_tool",
            baseline_score=0.7,
            tool_score=0.8,
            improvement_percent=14.3,
            sample_size=100,
            passed=True,
        )
        result = BuildResult(
            proposal=proposal,
            tool=tool,
            backtest=backtest,
            passed=True,
        )
        assert result.passed is True
        assert result.tool is not None
        assert result.backtest is not None
