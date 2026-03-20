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
            str(BRIDGE_CLI),
            "--command",
            command,
            "--args",
            json.dumps(args),
        ],
        capture_output=True,
        text=True,
        timeout=30,
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
                [sys.executable, str(BRIDGE_CLI), "--command", "nonexistent", "--args", "{}"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )


class TestBridgeCLIMalformedArgs:
    """Test malformed args JSON handling."""

    def test_malformed_json_args_returns_error(self) -> None:
        """Test that malformed JSON args returns error response."""
        result = subprocess.run(
            [sys.executable, str(BRIDGE_CLI), "--command", "blueprint_list", "--args", "not json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        response = json.loads(result.stdout)
        assert response["success"] is False
        assert "error" in response

    def test_empty_args_uses_defaults(self, tmp_path: Path) -> None:
        """Test that empty args dict uses defaults."""
        result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_CLI),
                "--command",
                "mesh_flow_state",
                "--args",
                "{}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
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
            [sys.executable, str(BRIDGE_CLI), "--command", "blueprint_list", "--args", "invalid"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        response = json.loads(result.stdout)
        assert response["success"] is False
        assert "error" in response

    def test_no_stderr_in_stdout(self, tmp_path: Path) -> None:
        """Test that debug logs go to stderr, not stdout."""
        result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_CLI),
                "--command",
                "mesh_flow_state",
                "--args",
                "{}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
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
