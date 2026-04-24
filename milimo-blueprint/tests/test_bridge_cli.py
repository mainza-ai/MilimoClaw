#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Pytest tests for bridge_cli.py

Tests cover:
- Valid command routing
- Unknown command error handling
- Malformed args JSON handling
- Python exception wrapping
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

BRIDGE_CLI = Path(__file__).parent.parent / "orchestrator" / "bridge_cli.py"


def run_bridge_cli(command: str, args: dict) -> dict:
    """Helper to run bridge_cli.py with given command and args."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.bridge_cli",
            "--command",
            command,
            "--args",
            json.dumps(args),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent),
    )
    return json.loads(result.stdout)


class TestBridgeCLIValidCommands:
    """Test valid command routing."""

    def test_blueprint_list_command(self, tmp_path: Path) -> None:
        """Test blueprint_list command returns valid JSON."""
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
            "blueprint_dir": str(tmp_path),
        }
        response = run_bridge_cli("blueprint_list", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_blueprint_info_command(self, tmp_path: Path) -> None:
        """Test blueprint_info command returns valid JSON."""
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
            "blueprint_dir": str(tmp_path),
        }
        response = run_bridge_cli("blueprint_info", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_evolution_status_command(self, tmp_path: Path) -> None:
        """Test evolution_status command returns valid JSON."""
        args = {
            "squad_id": "test-squad",
            "claw": "content",
            "blueprint_dir": str(tmp_path),
        }
        response = run_bridge_cli("evolution_status", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_tool_registry_command(self) -> None:
        """Test tool_registry command returns valid JSON."""
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
        }
        response = run_bridge_cli("tool_registry", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_marketplace_search_command(self) -> None:
        """Test marketplace_search command returns valid JSON."""
        args = {
            "query": "content",
            "category": "",
        }
        response = run_bridge_cli("marketplace_search", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_mesh_flow_state_command(self) -> None:
        """Test mesh_flow_state command returns valid JSON."""
        args = {"squad": "test-squad"}
        response = run_bridge_cli("mesh_flow_state", args)
        assert "success" in response
        assert isinstance(response["success"], bool)

    def test_health_status_command(self) -> None:
        """Test health_status command returns valid JSON."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("health_status", args)
        assert "success" in response
        assert isinstance(response["success"], bool)


class TestBridgeCLIUnknownCommand:
    """Test unknown command error handling."""

    def test_unknown_command_returns_error(self) -> None:
        """Test that unknown command returns error response."""
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "orchestrator.bridge_cli",
                    "--command",
                    "nonexistent",
                    "--args",
                    "{}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
                cwd=str(Path(__file__).parent.parent),
            )


class TestBridgeCLIMalformedArgs:
    """Test malformed args JSON handling."""

    def test_malformed_json_args_returns_error(self) -> None:
        """Test that malformed JSON args returns error response."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator.bridge_cli",
                "--command",
                "blueprint_list",
                "--args",
                "not json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )
        response = json.loads(result.stdout)
        assert response["success"] is False
        assert "error" in response

    def test_empty_args_uses_defaults(self, tmp_path: Path) -> None:
        """Test that empty args dict uses defaults."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator.bridge_cli",
                "--command",
                "mesh_flow_state",
                "--args",
                "{}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )
        response = json.loads(result.stdout)
        assert response["success"] is True


class TestBridgeCLIExceptionWrapping:
    """Test Python exception wrapping."""

    def test_exception_returns_error_message(self) -> None:
        """Test that exceptions are wrapped in error response."""
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
            "blueprint_dir": "/nonexistent/path/that/does/not/exist",
        }
        response = run_bridge_cli("blueprint_info", args)
        assert response["success"] is False
        assert "error" in response


class TestBridgeCLIResponseFormat:
    """Test response format compliance."""

    def test_success_response_has_data(self, tmp_path: Path) -> None:
        """Test that successful response has data field."""
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
            "blueprint_dir": str(tmp_path),
        }
        response = run_bridge_cli("blueprint_list", args)
        if response["success"]:
            assert "data" in response

    def test_error_response_has_message(self) -> None:
        """Test that error response has error field."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator.bridge_cli",
                "--command",
                "blueprint_list",
                "--args",
                "invalid",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )
        response = json.loads(result.stdout)
        assert response["success"] is False
        assert "error" in response

    def test_no_stderr_in_stdout(self, tmp_path: Path) -> None:
        """Test that debug logs go to stderr, not stdout."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator.bridge_cli",
                "--command",
                "mesh_flow_state",
                "--args",
                "{}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )
        stdout = result.stdout.strip()
        assert stdout.startswith("{")
        assert stdout.endswith("}")


class TestBridgeCLIEdgeCases:
    """Test edge cases."""

    def test_unicode_in_args(self) -> None:
        """Test that unicode characters in args are handled."""
        args = {"squad": "test-ño squad"}
        response = run_bridge_cli("mesh_flow_state", args)
        assert "success" in response

    def test_special_characters_in_path(self, tmp_path: Path) -> None:
        """Test special characters in blueprint path."""
        special_dir = tmp_path / "path with spaces"
        special_dir.mkdir()
        args = {
            "squad_id": "test-squad",
            "claw_role": "content",
            "blueprint_dir": str(special_dir),
        }
        response = run_bridge_cli("blueprint_list", args)
        assert "success" in response

    def test_empty_command_args(self) -> None:
        """Test command with no required args."""
        response = run_bridge_cli("mesh_flow_state", {})
        assert "success" in response


class TestBridgeCLIDigestCommands:
    """Test morning_brief and evening_wrap digest commands."""

    def test_morning_brief_command(self) -> None:
        """Test morning_brief command returns valid JSON."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("morning_brief", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert "overnight_actions" in data
        assert "queue_summary" in data
        assert "pending_actions" in data

    def test_evening_wrap_command(self) -> None:
        """Test evening_wrap command returns valid JSON."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("evening_wrap", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert "today_completed" in data
        assert "auto_executed" in data
        assert "remaining_pending" in data

    def test_morning_brief_with_empty_log(self, tmp_path: Path) -> None:
        """Test morning_brief handles empty log gracefully."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("morning_brief", args)
        assert response["success"] is True
        data = response["data"]
        assert data["overnight_actions"] == 0
        assert isinstance(data["pending_actions"], list)

    def test_evening_wrap_with_empty_log(self) -> None:
        """Test evening_wrap handles empty log gracefully."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("evening_wrap", args)
        assert response["success"] is True
        data = response["data"]
        assert data["today_completed"] == 0
        assert data["auto_executed"] == 0

    def test_morning_brief_queue_summary_structure(self) -> None:
        """Test morning_brief queue_summary has correct structure."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("morning_brief", args)
        assert response["success"] is True
        queue_summary = response["data"]["queue_summary"]
        assert "hold" in queue_summary
        assert "review" in queue_summary
        assert "auto" in queue_summary


class TestBridgeCLIRevenueCommand:
    """Test revenue_summary command."""

    def test_revenue_summary_command(self) -> None:
        """Test revenue_summary command returns valid JSON."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("revenue_summary", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert "week_revenue" in data
        assert "week_over_week_pct" in data
        assert "invoices_paid" in data
        assert "invoices_pending" in data
        assert "last_updated" in data

    def test_revenue_summary_missing_file(self) -> None:
        """Test revenue_summary handles missing file gracefully."""
        args = {"squad_id": "test-squad", "sandbox_dir": "/nonexistent"}
        response = run_bridge_cli("revenue_summary", args)
        assert response["success"] is True
        data = response["data"]
        assert data["week_revenue"] == 0.0
        assert data["week_over_week_pct"] == 0.0
        assert data["invoices_paid"] == 0
        assert data["invoices_pending"] == 0


class TestBridgeCLIDeepWorkCommands:
    """Test deep work mode commands."""

    def test_activate_deep_work_command(self, tmp_path: Path) -> None:
        """Test activate_deep_work command."""
        args = {"resume_date": "2026-04-01"}
        response = run_bridge_cli("activate_deep_work", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert data["active"] is True
        assert "activated_at" in data
        assert "resume_date" in data
        assert "policy_changes" in data

    def test_activate_deep_work_policy_changes(self, tmp_path: Path) -> None:
        """Test activate_deep_work returns policy changes per claw."""
        args = {"resume_date": "2026-04-01"}
        response = run_bridge_cli("activate_deep_work", args)
        assert response["success"] is True
        policy_changes = response["data"]["policy_changes"]
        assert len(policy_changes) == 6
        for change in policy_changes:
            assert "claw" in change
            assert "previous" in change
            assert "new" in change

    def test_activate_deep_work_blocked_actions(self, tmp_path: Path) -> None:
        """Test activate_deep_work includes blocked actions."""
        args = {"resume_date": "2026-04-01"}
        response = run_bridge_cli("activate_deep_work", args)
        assert response["success"] is True
        policy_changes = response["data"]["policy_changes"]
        content_change = next(c for c in policy_changes if c["claw"] == "content")
        assert "blocked_actions" in content_change
        assert len(content_change["blocked_actions"]) > 0

    def test_resume_deep_work_command(self, tmp_path: Path) -> None:
        """Test resume_deep_work command."""
        args = {}
        response = run_bridge_cli("resume_deep_work", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert data["active"] is False
        assert "policies_restored" in data

    def test_deep_work_status_command(self) -> None:
        """Test deep_work_status command."""
        args = {}
        response = run_bridge_cli("deep_work_status", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert "active" in data

    def test_activate_deep_work_missing_resume_date(self) -> None:
        """Test activate_deep_work requires resume_date."""
        args = {}
        response = run_bridge_cli("activate_deep_work", args)
        assert response["success"] is False
        assert "error" in response

    def test_activate_deep_work_invalid_date_format(self) -> None:
        """Test activate_deep_work validates date format."""
        args = {"resume_date": "invalid-date"}
        response = run_bridge_cli("activate_deep_work", args)
        assert response["success"] is False
        assert "error" in response


class TestBridgeCLICollectHealth:
    """Test collect_health command."""

    def test_collect_health_command(self) -> None:
        """Test collect_health returns valid JSON."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("collect_health", args)
        assert response["success"] is True
        assert "data" in response
        data = response["data"]
        assert "content" in data
        assert "ops" in data
        assert "analytics" in data
        assert "finance" in data
        assert "build" in data

    def test_collect_health_output_structure(self) -> None:
        """Test collect_health has correct structure per claw."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("collect_health", args)
        assert response["success"] is True
        content_health = response["data"]["content"]
        assert "role" in content_health
        assert "status" in content_health
        assert "tool_count" in content_health
        assert "last_evolution" in content_health
        assert "last_action" in content_health
        assert "actions_this_week" in content_health
        assert "sparkline" in content_health

    def test_collect_health_sparkline_seven_days(self) -> None:
        """Test collect_health sparkline has 7 values."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("collect_health", args)
        assert response["success"] is True
        sparkline = response["data"]["content"]["sparkline"]
        assert len(sparkline) == 7
        for val in sparkline:
            assert isinstance(val, int)

    def test_collect_health_missing_logs(self) -> None:
        """Test collect_health handles missing logs gracefully."""
        args = {"squad_id": "nonexistent-squad"}
        response = run_bridge_cli("collect_health", args)
        assert response["success"] is True
        data = response["data"]
        for role in ["content", "ops", "analytics", "finance", "build"]:
            assert data[role]["tool_count"] >= 0
            assert data[role]["actions_this_week"] >= 0

    def test_collect_health_status_values(self) -> None:
        """Test collect_health returns valid status values."""
        args = {"squad_id": "test-squad"}
        response = run_bridge_cli("collect_health", args)
        assert response["success"] is True
        valid_statuses = {"active", "idle", "processing", "error"}
        for role in ["content", "ops", "analytics", "finance", "build"]:
            assert response["data"][role]["status"] in valid_statuses
