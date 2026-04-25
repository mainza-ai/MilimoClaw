# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for solo_init.py - Template Loader
"""

from pathlib import Path
from typing import Any

import pytest

from orchestrator.solo_init import (
    load_solo_founder_template,
    MissingFieldError,
    InvalidFieldTypeError,
    TemplateValidationError,
    get_claw_paths,
    get_claw_network_policy,
    get_approval_modes,
    get_evolution_config,
)


# ---------------------------------------------------------------------------

VALID_TEMPLATE = """
template:
  name: solo-founder
  display_name: "Solo Founder"
  category: founder
  description: "All five claws on one machine"
  squad_size: 1
  claws_active:
    - content
    - ops
    - analytics
    - finance
    - build

operator_policy:
  squad_lead: mainza
  approval_modes:
    content:
      social_post_draft: AUTO
      client_proposal_draft: REVIEW
    ops:
      new_client_inquiry: REVIEW
      welcome_message: AUTO
    analytics:
      weekly_report: AUTO
      anomaly_alert: REVIEW
    finance:
      invoice_generation: REVIEW
      invoice_send: HOLD
    build:
      pr_open: REVIEW
      pr_merge: HOLD

filesystem:
  content: /sandbox/content
  ops: /sandbox/clients
  analytics: /sandbox/analytics
  finance: /sandbox/finance
  build: /sandbox/build
  shared_read:
    - /sandbox/analytics/reports/weekly-intelligence.json

inference:
  solo_mode: true
  routing_overrides:
    client_facing_drafts: cloud
    internal_ideation: local
    financial_data: local
    source_code: local
  cost_guard:
    daily_cloud_token_budget: 50000
    alert_at_percent: 80
    fallback_on_exceed: local

war_room:
  operator: mainza
  mode: solo
  queue_priority:
    1: HOLD
    2: REVIEW
    3: AUTO
  digest_schedule:
    morning_brief: "07:00"
    evening_wrap: "20:00"
  evolution_log:
    show_on_startup: true
    require_ack: false
  escalation:
    urgent_channels:
      - war_room_tui
      - cli_notification

evolution:
  cycle_day: "sunday"
  schedule:
    time: "02:00"
    cycle: weekly
  per_claw:
    content:
      enabled: true
      min_approved_posts: 10
      performance_threshold: 5
    ops:
      enabled: true
      min_client_interactions: 5
      performance_threshold: 5
    analytics:
      enabled: true
      min_data_weeks: 3
      performance_threshold: 5
    finance:
      enabled: true
      min_invoices: 3
      performance_threshold: 5
    build:
      enabled: true
      min_prs_merged: 5
      performance_threshold: 5
  capacity:
    max_tools_per_claw: 30
    evolution_log_retention: 90

network_egress:
  content:
    approved:
      - api.twitter.com
      - api.instagram.com
  ops:
    approved:
      - api.gmail.com
      - api.notion.com
  analytics:
    approved:
      - api.twitter.com
  finance:
    approved:
      - api.stripe.com
  build:
    approved:
      - api.github.com
      - api.vercel.com

deep_work_mode:
  alias: finals-mode
  on_activate:
    content: pause_drafts
    ops: maintenance
    analytics: passive
    finance: invoices_only
    build: issues_only
  auto_response_template: "Hey [name], I'm heads-down until [resume_date]."
  resume_on: scheduled
"""


# ---------------------------------------------------------------------------


class TestLoadSoloFounderTemplate:
    """Tests for load_solo_founder_template function."""

    def test_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid template configuration."""
        template_file = tmp_path / "solo-founder.yaml"
        template_file.write_text(VALID_TEMPLATE)

        config = load_solo_founder_template(str(template_file))

        assert config is not None
        assert config["template"]["name"] == "solo-founder"
        assert config["template"]["squad_size"] == 1
        assert len(config["template"]["claws_active"]) == 5
        assert "operator_policy" in config
        assert "filesystem" in config
        assert "inference" in config

    def test_missing_file(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        missing_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_solo_founder_template(str(missing_file))

    def test_missing_required_field_template_name(self, tmp_path: Path) -> None:
        """Test that MissingFieldError is raised when template.name is missing."""
        invalid_template = VALID_TEMPLATE.replace("name: solo-founder", "")
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(MissingFieldError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "template.name" in str(exc_info.value)

    def test_missing_required_field_filesystem_claw(self, tmp_path: Path) -> None:
        """Test that MissingFieldError is raised when a claw path is missing."""
        invalid_template = VALID_TEMPLATE.replace("content: /sandbox/content", "")
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(MissingFieldError):
            load_solo_founder_template(str(template_file))

    def test_missing_required_section(self, tmp_path: Path) -> None:
        """Test that MissingFieldError is raised when a required section is missing."""
        invalid_template = VALID_TEMPLATE.replace(
            "operator_policy:", "removed_section:"
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(MissingFieldError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "operator_policy" in str(exc_info.value)

    def test_invalid_field_type_squad_size(self, tmp_path: Path) -> None:
        """Test that InvalidFieldTypeError is raised for wrong type."""
        invalid_template = VALID_TEMPLATE.replace("squad_size: 1", 'squad_size: "one"')
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(InvalidFieldTypeError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "squad_size" in str(exc_info.value)

    def test_invalid_field_type_claws_active(self, tmp_path: Path) -> None:
        """Test that InvalidFieldTypeError is raised when claws_active is not a list."""
        invalid_template = VALID_TEMPLATE.replace(
            "claws_active:\n    - content\n    - ops\n    - analytics\n    - finance\n    - build",
            "claws_active: content",
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(InvalidFieldTypeError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "claws_active" in str(exc_info.value)

    def test_invalid_claw_name_in_claws_active(self, tmp_path: Path) -> None:
        """Test that InvalidFieldTypeError is raised for invalid claw name."""
        invalid_template = VALID_TEMPLATE.replace("- build", "- invalid_claw")
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(InvalidFieldTypeError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "invalid_claw" in str(exc_info.value)

    def test_locked_route_financial_data_not_local(self, tmp_path: Path) -> None:
        """Test that TemplateValidationError is raised when locked route is not 'local'."""
        invalid_template = VALID_TEMPLATE.replace(
            "financial_data: local", "financial_data: cloud"
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(TemplateValidationError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "financial_data" in str(exc_info.value)
        assert "must be 'local'" in str(exc_info.value)

    def test_locked_route_source_code_not_local(self, tmp_path: Path) -> None:
        """Test that TemplateValidationError is raised when source_code is not 'local'."""
        invalid_template = VALID_TEMPLATE.replace(
            "source_code: local", "source_code: cloud"
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(TemplateValidationError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "source_code" in str(exc_info.value)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that TemplateValidationError is raised for empty file."""
        template_file = tmp_path / "empty.yaml"
        template_file.write_text("")

        with pytest.raises(TemplateValidationError):
            load_solo_founder_template(str(template_file))

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that TemplateValidationError is raised for invalid YAML."""
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text("invalid: yaml: content:\n  - broken")

        with pytest.raises(TemplateValidationError):
            load_solo_founder_template(str(template_file))

    def test_missing_evolution_per_claw(self, tmp_path: Path) -> None:
        """Test that MissingFieldError is raised when evolution.per_claw is missing a claw."""
        invalid_template = VALID_TEMPLATE.replace(
            "build:\n      enabled: true\n      min_prs_merged: 5\n      performance_threshold: 5",
            "",
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(MissingFieldError) as exc_info:
            load_solo_founder_template(str(template_file))

        assert "build" in str(exc_info.value)

    def test_missing_approval_mode_claw(self, tmp_path: Path) -> None:
        """Test that MissingFieldError is raised when approval_modes is missing a claw."""
        invalid_template = VALID_TEMPLATE.replace(
            "build:\n      pr_open: REVIEW\n      pr_merge: HOLD", ""
        )
        template_file = tmp_path / "invalid.yaml"
        template_file.write_text(invalid_template)

        with pytest.raises(MissingFieldError):
            load_solo_founder_template(str(template_file))


class TestHelperFunctions:
    """Tests for helper functions."""

    @pytest.fixture
    def valid_config(self, tmp_path: Path) -> dict[str, Any]:
        """Load a valid config for testing."""
        template_file = tmp_path / "solo-founder.yaml"
        template_file.write_text(VALID_TEMPLATE)
        return load_solo_founder_template(str(template_file))

    def test_get_claw_paths(self, valid_config: dict[str, Any]) -> None:
        """Test extracting claw paths from config."""
        paths = get_claw_paths(valid_config)

        assert len(paths) == 5
        assert paths["content"] == Path("/sandbox/content")
        assert paths["ops"] == Path("/sandbox/clients")
        assert paths["analytics"] == Path("/sandbox/analytics")
        assert paths["finance"] == Path("/sandbox/finance")
        assert paths["build"] == Path("/sandbox/build")

    def test_get_claw_network_policy(self, valid_config: dict[str, Any]) -> None:
        """Test extracting network policy for a claw."""
        policy = get_claw_network_policy(valid_config, "content")

        assert "approved" in policy
        assert "api.twitter.com" in policy["approved"]
        assert "api.instagram.com" in policy["approved"]

    def test_get_claw_network_policy_invalid_claw(
        self, valid_config: dict[str, Any]
    ) -> None:
        """Test that ValueError is raised for invalid claw name."""
        with pytest.raises(ValueError):
            get_claw_network_policy(valid_config, "invalid_claw")

    def test_get_approval_modes(self, valid_config: dict[str, Any]) -> None:
        """Test extracting approval modes from config."""
        modes = get_approval_modes(valid_config)

        assert len(modes) == 5
        assert "content" in modes
        assert modes["content"]["social_post_draft"] == "AUTO"
        assert modes["finance"]["invoice_send"] == "HOLD"

    def test_get_evolution_config(self, valid_config: dict[str, Any]) -> None:
        """Test extracting evolution config for a claw."""
        evo_config = get_evolution_config(valid_config, "content")

        assert evo_config["enabled"] is True
        assert evo_config["min_approved_posts"] == 10
        assert evo_config["performance_threshold"] == 5

    def test_get_evolution_config_invalid_claw(
        self, valid_config: dict[str, Any]
    ) -> None:
        """Test that ValueError is raised for invalid claw name."""
        with pytest.raises(ValueError):
            get_evolution_config(valid_config, "invalid_claw")
