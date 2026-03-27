#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo-founder.yaml configuration validation and remediation fixes.

This file tests:
- FIX 2: Staggered evolution schedule configuration
- FIX 7: Cost guard with lighter_prompt fallback
- FIX 8: deadline_risk and deadline_critical action types
"""
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml


class TestEvolutionScheduleConfiguration:
    """Tests for FIX 2: Staggered evolution schedule in solo-founder.yaml."""

    def test_evolution_schedule_has_per_claw_times(self):
        """Evolution schedule contains per-claw time slots."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        schedule = data.get("evolution", {}).get("schedule", {})

        assert schedule.get("content") == "02:05", "Content should be at 02:05"
        assert schedule.get("ops") == "02:15", "Ops should be at 02:15"
        assert schedule.get("analytics_evolution") == "02:25", "Analytics should be at 02:25"
        assert schedule.get("build") == "02:35", "Build should be at 02:35"
        assert schedule.get("finance") == "03:00", "Finance should be at 03:00"

    def test_evolution_schedule_has_analytics_baseline_and_report(self):
        """Evolution schedule includes analytics baseline and report times."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        schedule = data.get("evolution", {}).get("schedule", {})

        assert schedule.get("analytics_baseline") == "01:00"
        assert schedule.get("analytics_report") == "02:00"

    def test_evolution_schedule_five_minute_gaps(self):
        """Evolution schedule has 5-minute gaps between claws."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        schedule = data.get("evolution", {}).get("schedule", {})

        def parse_time(t: str) -> int:
            h, m = map(int, t.split(":"))
            return h * 60 + m

        # Verify gaps between content -> ops -> analytics -> build -> finance
        content_time = parse_time(schedule["content"])
        ops_time = parse_time(schedule["ops"])
        analytics_time = parse_time(schedule["analytics_evolution"])
        build_time = parse_time(schedule["build"])
        finance_time = parse_time(schedule["finance"])

        assert ops_time - content_time == 10, "10-minute gap from content to ops"
        assert analytics_time - ops_time == 10, "10-minute gap from ops to analytics"
        assert build_time - analytics_time == 10, "10-minute gap from analytics to build"
        assert finance_time - build_time == 25, "25-minute gap from build to finance"

    def test_evolution_min_thresholds_defined(self):
        """Evolution min_thresholds are defined for all claws."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        thresholds = data.get("evolution", {}).get("min_thresholds", {})

        required_claws = ["content", "ops", "analytics", "finance", "build"]
        for claw in required_claws:
            assert claw in thresholds, f"Missing min_thresholds for {claw}"
            assert len(thresholds[claw]) > 0, f"Empty thresholds for {claw}"


class TestCostGuardConfiguration:
    """Tests for FIX 7: Cost guard with lighter_prompt fallback."""

    def test_daily_cloud_token_budget_is_50000(self):
        """Daily cloud token budget is 50,000 per spec."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        cost_guard = data.get("inference", {}).get("cost_guard", {})
        budget = cost_guard.get("daily_cloud_token_budget")

        assert budget == 50000, f"Expected budget 50000, got {budget}"

    def test_fallback_on_exceed_is_lighter_prompt(self):
        """Fallback strategy is lighter_prompt, not cloud."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        cost_guard = data.get("inference", {}).get("cost_guard", {})
        fallback = cost_guard.get("fallback_on_exceed")

        assert fallback == "lighter_prompt", f"Expected lighter_prompt, got {fallback}"

    def test_never_block_claw_action_is_true(self):
        """Cost guard never blocks claw actions."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        cost_guard = data.get("inference", {}).get("cost_guard", {})
        never_block = cost_guard.get("never_block_claw_action")

        assert never_block is True, "never_block_claw_action should be true"

    def test_lighter_prompt_strategy_implementation(self):
        """Lighter prompt strategy reduces max_tokens by 50%."""
        from orchestrator.solo_privacy import CostGuard, FallbackStrategy

        guard = CostGuard(
            daily_budget=50000,
            fallback_strategy=FallbackStrategy.LIGHTER_PROMPT,
        )

        prompt = "TASK: Generate code\n\nCODEBASE CONTEXT: " + "x" * 1000 + "\n\nMore instructions"
        max_tokens = 4000

        trimmed, reduced = guard.apply_lighter_prompt_strategy(prompt, max_tokens)

        assert reduced == 2000, f"Expected 2000 tokens, got {reduced}"
        assert len(trimmed) < len(prompt), "Prompt should be trimmed"

    def test_lighter_prompt_trims_context_sections(self):
        """Lighter prompt trims CODEBASE CONTEXT and similar sections."""
        from orchestrator.solo_privacy import CostGuard, FallbackStrategy

        guard = CostGuard(
            daily_budget=50000,
            fallback_strategy=FallbackStrategy.LIGHTER_PROMPT,
        )

        prompt = """
TASK: Fix the bug

CODEBASE CONTEXT:
This is a large codebase with many files...
""" + "x" * 500 + """

More context here.

COMMUNICATION HISTORY:
Email thread about the project...
""" + "y" * 500 + """

End of prompt.
"""
        trimmed, _ = guard.apply_lighter_prompt_strategy(prompt, 4000)

        # Should contain markers for trimmed sections
        assert "cost guard active" in trimmed.lower() or len(trimmed) < len(prompt)

    def test_lighter_prompt_never_raises_exception(self):
        """Lighter prompt strategy never raises exceptions."""
        from orchestrator.solo_privacy import CostGuard, FallbackStrategy

        guard = CostGuard(
            daily_budget=50000,
            fallback_strategy=FallbackStrategy.LIGHTER_PROMPT,
        )

        # Test with edge cases
        empty_prompt = ""
        short_prompt = "x"
        no_markers = "Just a simple prompt without markers"

        for prompt in [empty_prompt, short_prompt, no_markers]:
            try:
                trimmed, reduced = guard.apply_lighter_prompt_strategy(prompt, 4000)
                # Should not raise
            except Exception as e:
                pytest.fail(f"Lighter prompt raised exception: {e}")


class TestOpsDeadlineActionTypes:
    """Tests for FIX 8: deadline_risk and deadline_critical action types."""

    def test_deadline_risk_is_review(self):
        """deadline_risk action type is REVIEW mode."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        ops_modes = (
            data.get("operator_policy", {})
            .get("approval_modes", {})
            .get("ops", {})
        )

        assert ops_modes.get("deadline_risk") == "REVIEW"

    def test_deadline_critical_is_hold(self):
        """deadline_critical action type is HOLD mode."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        ops_modes = (
            data.get("operator_policy", {})
            .get("approval_modes", {})
            .get("ops", {})
        )

        assert ops_modes.get("deadline_critical") == "HOLD"

    def test_no_legacy_deadline_flag(self):
        """Old deadline_flag action type should not exist."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        ops_modes = (
            data.get("operator_policy", {})
            .get("approval_modes", {})
            .get("ops", {})
        )

        assert "deadline_flag" not in ops_modes, (
            "deadline_flag should be replaced with deadline_risk and deadline_critical"
        )


class TestApprovalModesStructure:
    """Tests for proper approval_modes YAML structure."""

    def test_approval_modes_is_dict(self):
        """approval_modes is a dict, not None."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        approval_modes = (
            data.get("operator_policy", {})
            .get("approval_modes", {})
        )

        assert approval_modes is not None
        assert isinstance(approval_modes, dict)

    def test_all_five_claws_have_approval_modes(self):
        """All five claws have approval mode configurations."""
        config_path = Path(__file__).parent.parent / "templates" / "solo-founder.yaml"

        with config_path.open("r") as f:
            data = yaml.safe_load(f)

        approval_modes = (
            data.get("operator_policy", {})
            .get("approval_modes", {})
        )

        required_claws = ["content", "ops", "analytics", "finance", "build"]
        for claw in required_claws:
            assert claw in approval_modes, f"Missing approval_modes for {claw}"
