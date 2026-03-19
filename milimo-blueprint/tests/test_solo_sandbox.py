#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_sandbox.py - Sandbox Initializer
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from orchestrator.solo_sandbox import (
    init_solo_sandbox,
    SandboxPolicy,
    _determine_default_approval,
    _get_inference_routes,
    _write_sandbox_policy,
)


# ---------------------------------------------------------------------------

VALID_CONFIG: dict[str, Any] = {
    "template": {
        "name": "solo-founder",
        "claws_active": ["content", "ops", "analytics", "finance", "build"],
    },
    "filesystem": {
        "content": "/sandbox/content",
        "ops": "/sandbox/clients",
        "analytics": "/sandbox/analytics",
        "finance": "/sandbox/finance",
        "build": "/sandbox/build",
    },
    "network_egress": {
        "content": {"approved": ["api.twitter.com", "api.instagram.com"]},
        "ops": {"approved": ["api.gmail.com"]},
        "analytics": {"approved": ["api.twitter.com"]},
        "finance": {"approved": ["api.stripe.com"]},
        "build": {"approved": ["api.github.com"]},
    },
    "operator_policy": {
        "approval_modes": {
            "content": {"social_post_draft": "AUTO", "client_proposal_draft": "REVIEW"},
            "ops": {"new_client_inquiry": "REVIEW", "welcome_message": "AUTO"},
            "analytics": {"weekly_report": "AUTO"},
            "finance": {"invoice_generation": "REVIEW", "invoice_send": "HOLD"},
            "build": {"pr_open": "REVIEW", "pr_merge": "HOLD"},
        },
    },
    "inference": {
        "routing_overrides": {
            "client_facing_drafts": "cloud",
            "internal_ideation": "local",
            "financial_data": "local",
            "source_code": "local",
            "analytics_synthesis": "local",
            "public_docs_changelogs": "cloud",
        },
    },
}


# ---------------------------------------------------------------------------

class TestInitSoloSandbox:
    """Tests for init_solo_sandbox function."""

    def test_creates_all_policies(self, tmp_path: Path) -> None:
        """Test that policies are created for all claws."""
        result = init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        assert result["summary"]["claws_initialized"] == 5
        assert len(result["policies"]) == 5
        assert len(result["directories"]) == 5

    def test_creates_policy_files(self, tmp_path: Path) -> None:
        """Test that policy files are created."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        for claw in ["content", "ops", "analytics", "finance", "build"]:
            policy_file = tmp_path / f"{claw}-claw.yaml"
            assert policy_file.exists()

    def test_policy_file_structure(self, tmp_path: Path) -> None:
        """Test that policy files have correct structure."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "content-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        assert "metadata" in policy
        assert "filesystem" in policy
        assert "network" in policy
        assert "inference" in policy
        assert "operator_policy" in policy
        assert "security" in policy

    def test_policy_has_correct_mount(self, tmp_path: Path) -> None:
        """Test that policy has correct mount path."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "content-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        assert policy["filesystem"]["mount"] == "/sandbox/content"

    def test_policy_has_network_egress(self, tmp_path: Path) -> None:
        """Test that policy has network egress configuration."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "content-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        assert "api.twitter.com" in policy["network"]["approved_domains"]
        assert "api.instagram.com" in policy["network"]["approved_domains"]

    def test_policy_has_inference_routes(self, tmp_path: Path) -> None:
        """Test that policy has inference routing configuration."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "content-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        routes = policy["inference"]["routing"]
        assert "client_facing_drafts" in routes
        assert routes["client_facing_drafts"] == "cloud"

    def test_finance_claw_locked_routes(self, tmp_path: Path) -> None:
        """Test that finance claw has locked routes."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "finance-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        routes = policy["inference"]["routing"]
        assert routes["financial_data"] == "local"

    def test_build_claw_locked_routes(self, tmp_path: Path) -> None:
        """Test that build claw has locked routes."""
        init_solo_sandbox(VALID_CONFIG, base_dir=tmp_path)

        policy_file = tmp_path / "build-claw.yaml"
        with policy_file.open("r") as f:
            policy = yaml.safe_load(f)

        routes = policy["inference"]["routing"]
        assert routes["source_code"] == "local"


class TestDetermineDefaultApproval:
    """Tests for _determine_default_approval function."""

    def test_returns_hold_when_present(self) -> None:
        """Test that HOLD is returned when any action is HOLD."""
        modes = {"action1": "AUTO", "action2": "HOLD", "action3": "REVIEW"}
        assert _determine_default_approval(modes) == "HOLD"

    def test_returns_review_when_majority(self) -> None:
        """Test that REVIEW is returned when it's the majority."""
        modes = {"action1": "AUTO", "action2": "REVIEW", "action3": "REVIEW"}
        assert _determine_default_approval(modes) == "REVIEW"

    def test_returns_auto_when_majority(self) -> None:
        """Test that AUTO is returned when it's the majority."""
        modes = {"action1": "AUTO", "action2": "AUTO", "action3": "REVIEW"}
        assert _determine_default_approval(modes) == "AUTO"

    def test_returns_review_when_empty(self) -> None:
        """Test that REVIEW is returned for empty modes."""
        assert _determine_default_approval({}) == "REVIEW"

    def test_returns_hold_with_multiple_holds(self) -> None:
        """Test that HOLD is returned when multiple HOLD actions."""
        modes = {"action1": "HOLD", "action2": "HOLD", "action3": "AUTO"}
        assert _determine_default_approval(modes) == "HOLD"


class TestGetInferenceRoutes:
    """Tests for _get_inference_routes function."""

    def test_content_claw_routes(self) -> None:
        """Test content claw inference routes."""
        routing_overrides = {
            "client_facing_drafts": "cloud",
            "public_docs_changelogs": "cloud",
            "internal_ideation": "local",
        }
        routes = _get_inference_routes("content", routing_overrides)

        assert routes["client_facing_drafts"] == "cloud"
        assert routes["public_docs_changelogs"] == "cloud"
        assert routes["financial_data"] == "local"
        assert routes["source_code"] == "local"

    def test_finance_claw_has_locked_routes(self) -> None:
        """Test that finance claw always has locked routes."""
        routing_overrides = {"client_facing_drafts": "cloud"}
        routes = _get_inference_routes("finance", routing_overrides)

        assert routes["financial_data"] == "local"

    def test_build_claw_has_locked_routes(self) -> None:
        """Test that build claw always has locked routes."""
        routing_overrides = {"client_facing_drafts": "cloud"}
        routes = _get_inference_routes("build", routing_overrides)

        assert routes["source_code"] == "local"

    def test_ops_claw_routes(self) -> None:
        """Test ops claw inference routes."""
        routing_overrides = {
            "client_records": "local",
            "internal_ideation": "local",
        }
        routes = _get_inference_routes("ops", routing_overrides)

        assert routes["client_records"] == "local"
        assert routes["internal_ideation"] == "local"

    def test_locked_routes_not_overridden(self) -> None:
        """Test that locked routes cannot be overridden."""
        routing_overrides = {
            "financial_data": "cloud",
            "source_code": "cloud",
        }
        routes = _get_inference_routes("finance", routing_overrides)

        assert routes["financial_data"] == "local"


class TestWriteSandboxPolicy:
    """Tests for _write_sandbox_policy function."""

    def test_writes_valid_yaml(self, tmp_path: Path) -> None:
        """Test that valid YAML is written."""
        policy = SandboxPolicy(
            claw="content",
            mount="/sandbox/content",
            network_egress=["api.twitter.com"],
            inference_routes={"client_facing_drafts": "cloud"},
            approval_mode="REVIEW",
        )

        output_file = tmp_path / "test-policy.yaml"
        _write_sandbox_policy(policy, output_file)

        assert output_file.exists()

        with output_file.open("r") as f:
            loaded = yaml.safe_load(f)

        assert loaded is not None

    def test_includes_all_sections(self, tmp_path: Path) -> None:
        """Test that all required sections are included."""
        policy = SandboxPolicy(
            claw="content",
            mount="/sandbox/content",
            network_egress=["api.twitter.com"],
            inference_routes={},
            approval_mode="AUTO",
        )

        output_file = tmp_path / "test-policy.yaml"
        _write_sandbox_policy(policy, output_file)

        with output_file.open("r") as f:
            loaded = yaml.safe_load(f)

        assert "metadata" in loaded
        assert "filesystem" in loaded
        assert "network" in loaded
        assert "inference" in loaded
        assert "operator_policy" in loaded
        assert "security" in loaded

    def test_metadata_section(self, tmp_path: Path) -> None:
        """Test that metadata section is correct."""
        policy = SandboxPolicy(
            claw="ops",
            mount="/sandbox/clients",
            network_egress=[],
            inference_routes={},
            approval_mode="REVIEW",
        )

        output_file = tmp_path / "test-policy.yaml"
        _write_sandbox_policy(policy, output_file)

        with output_file.open("r") as f:
            loaded = yaml.safe_load(f)

        assert loaded["metadata"]["claw"] == "ops"
        assert loaded["metadata"]["schema"] == "nemoClaw-sandbox-policy-v1"
