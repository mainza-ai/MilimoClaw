#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_deep_work.py - Deep Work Mode
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from orchestrator.solo_deep_work import (
    activate_deep_work_mode,
    deactivate_deep_work_mode,
    get_deep_work_status,
    is_deep_work_active,
    DeepWorkState,
    ClawPolicyUpdate,
    DEEP_WORK_POLICIES,
    CLAW_ON_ACTIVATE_MAP,
)


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "deep_work_mode": {
        "alias": "finals-mode",
        "on_activate": {
            "content": "pause_drafts",
            "ops": "maintenance",
            "analytics": "passive",
            "finance": "invoices_only",
            "build": "issues_only",
        },
        "auto_response_template": "Hey [name], I'm heads-down until [resume_date].",
        "resume_on": "scheduled",
    },
}


# ---------------------------------------------------------------------------

class TestActivateDeepWorkMode:
    """Tests for activate_deep_work_mode function."""

    def test_basic_activation(self, tmp_path: Path) -> None:
        """Test basic deep work activation."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        result = activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert result["active"] is True
        assert "2026-04-01" in result["resume_date"]
        assert len(result["policy_changes"]) == 5

    def test_resume_date_substituted_in_template(self, tmp_path: Path) -> None:
        """Test that resume_date is substituted in auto_response."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        result = activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-15",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert "2026-04-15" in result["auto_response"]
        assert "[resume_date]" not in result["auto_response"]

    def test_policy_changes_recorded(self, tmp_path: Path) -> None:
        """Test that policy changes are recorded."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        result = activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        content_change = next(
            (c for c in result["policy_changes"] if c["claw"] == "content"),
            None
        )

        assert content_change is not None
        assert content_change["new"] == "pause_drafts"
        assert "publish" in content_change["blocked_actions"]

    def test_state_file_created(self, tmp_path: Path) -> None:
        """Test that state file is created."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert state_file.exists()

        with state_file.open("r") as f:
            state = json.load(f)

        assert state["active"] is True
        assert state["resume_date"] is not None

    def test_policy_file_updated(self, tmp_path: Path) -> None:
        """Test that policy files are updated."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        content_policy = policy_dir / "content-claw.yaml"
        with content_policy.open("w") as f:
            yaml.dump({"claw": "content", "version": "1.0"}, f)

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        with content_policy.open("r") as f:
            policy = yaml.safe_load(f)

        assert policy["deep_work_policy"] == "pause_drafts"
        assert policy["deep_work_active"] is True

    def test_invalid_resume_date(self, tmp_path: Path) -> None:
        """Test that invalid resume_date raises error."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        with pytest.raises(ValueError):
            activate_deep_work_mode(
                VALID_CONFIG,
                "invalid-date",
                policy_dir=policy_dir,
                state_file=state_file,
            )

    def test_all_claws_updated(self, tmp_path: Path) -> None:
        """Test that all five claws are updated."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        result = activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        claws_updated = {c["claw"] for c in result["policy_changes"]}

        assert claws_updated == {"content", "ops", "analytics", "finance", "build"}

    def test_blocked_actions_per_claw(self, tmp_path: Path) -> None:
        """Test that correct actions are blocked per claw."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        result = activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        for change in result["policy_changes"]:
            if change["claw"] == "content":
                assert "publish" in change["blocked_actions"]
            elif change["claw"] == "ops":
                assert "new_outreach" in change["blocked_actions"]
            elif change["claw"] == "build":
                assert "open_pr" in change["blocked_actions"]


class TestDeactivateDeepWorkMode:
    """Tests for deactivate_deep_work_mode function."""

    def test_basic_deactivation(self, tmp_path: Path) -> None:
        """Test basic deactivation."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        result = deactivate_deep_work_mode(
            VALID_CONFIG,
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert result["active"] is False
        assert "policies_restored" in result

    def test_state_file_cleared(self, tmp_path: Path) -> None:
        """Test that state file is cleared."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        deactivate_deep_work_mode(
            VALID_CONFIG,
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert not state_file.exists()

    def test_policy_restored(self, tmp_path: Path) -> None:
        """Test that policies are restored."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        content_policy = policy_dir / "content-claw.yaml"
        with content_policy.open("w") as f:
            yaml.dump({"claw": "content"}, f)

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        deactivate_deep_work_mode(
            VALID_CONFIG,
            policy_dir=policy_dir,
            state_file=state_file,
        )

        with content_policy.open("r") as f:
            policy = yaml.safe_load(f)

        assert "deep_work_policy" not in policy
        assert "deep_work_active" not in policy

    def test_deactivation_without_activation(self, tmp_path: Path) -> None:
        """Test deactivation when not active."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"

        result = deactivate_deep_work_mode(
            VALID_CONFIG,
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert result["active"] is False
        assert "not active" in result["message"]


class TestGetDeepWorkStatus:
    """Tests for get_deep_work_status function."""

    def test_status_when_active(self, tmp_path: Path) -> None:
        """Test status when deep work is active."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        status = get_deep_work_status(state_file)

        assert status["active"] is True
        assert "resume_date" in status

    def test_status_when_inactive(self, tmp_path: Path) -> None:
        """Test status when deep work is not active."""
        state_file = tmp_path / "deep_work.json"

        status = get_deep_work_status(state_file)

        assert status["active"] is False


class TestIsDeepWorkActive:
    """Tests for is_deep_work_active function."""

    def test_true_when_active(self, tmp_path: Path) -> None:
        """Test returns True when active."""
        state_file = tmp_path / "deep_work.json"
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()

        activate_deep_work_mode(
            VALID_CONFIG,
            "2026-04-01",
            policy_dir=policy_dir,
            state_file=state_file,
        )

        assert is_deep_work_active(state_file) is True

    def test_false_when_inactive(self, tmp_path: Path) -> None:
        """Test returns False when inactive."""
        state_file = tmp_path / "deep_work.json"

        assert is_deep_work_active(state_file) is False


class TestDeepWorkState:
    """Tests for DeepWorkState dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        state = DeepWorkState()

        assert state.active is False
        assert state.activated_at is None
        assert state.resume_date is None
        assert state.auto_response_template == ""


class TestClawPolicyUpdate:
    """Tests for ClawPolicyUpdate dataclass."""

    def test_required_fields(self) -> None:
        """Test required fields."""
        update = ClawPolicyUpdate(
            claw="content",
            previous_policy="normal",
            new_policy="pause_drafts",
        )

        assert update.claw == "content"
        assert update.previous_policy == "normal"
        assert update.new_policy == "pause_drafts"


class TestConstants:
    """Tests for module constants."""

    def test_deep_work_policies_defined(self) -> None:
        """Test that all policies are defined."""
        assert "pause_drafts" in DEEP_WORK_POLICIES
        assert "maintenance" in DEEP_WORK_POLICIES
        assert "passive" in DEEP_WORK_POLICIES
        assert "invoices_only" in DEEP_WORK_POLICIES
        assert "issues_only" in DEEP_WORK_POLICIES

    def test_policies_have_blocked_actions(self) -> None:
        """Test that policies define blocked actions."""
        for policy_name, policy in DEEP_WORK_POLICIES.items():
            assert "actions_blocked" in policy
            assert isinstance(policy["actions_blocked"], list)

    def test_claw_on_activate_map(self) -> None:
        """Test that all claws have on_activate mapping."""
        assert CLAW_ON_ACTIVATE_MAP["content"] == "pause_drafts"
        assert CLAW_ON_ACTIVATE_MAP["ops"] == "maintenance"
        assert CLAW_ON_ACTIVATE_MAP["analytics"] == "passive"
        assert CLAW_ON_ACTIVATE_MAP["finance"] == "invoices_only"
        assert CLAW_ON_ACTIVATE_MAP["build"] == "issues_only"
