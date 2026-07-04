# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for containment.py - Process Containment Sandboxing
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from milimo_core.containment import get_contained_command


def test_get_contained_command_bwrap_available() -> None:
    """Verify that get_contained_command wraps command with bwrap if available."""
    base_args = ["python", "-m", "pytest"]
    work_dir = Path("/tmp/mock-repo")
    clean_env = {"PATH": "/usr/bin"}

    def mock_which(name: str) -> str | None:
        if name == "bwrap":
            return "/usr/bin/bwrap"
        return None

    with patch("shutil.which", side_effect=mock_which), \
         patch("os.path.exists", return_value=True):
        cmd = get_contained_command(base_args, work_dir, clean_env)

        assert cmd[0] == "/usr/bin/bwrap"
        assert "--unshare-all" in cmd
        assert "--proc" in cmd
        assert "--dev" in cmd
        assert "--bind" in cmd
        assert str(work_dir.resolve()) in cmd
        assert cmd[-3:] == base_args


def test_get_contained_command_docker_available_and_active() -> None:
    """Verify that get_contained_command wraps command with docker if bwrap is missing and docker daemon is active."""
    base_args = ["python", "-m", "pytest"]
    work_dir = Path("/tmp/mock-repo")
    clean_env = {"PATH": "/usr/bin"}

    def mock_which(name: str) -> str | None:
        if name == "docker":
            return "/usr/bin/docker"
        return None

    with patch("shutil.which", side_effect=mock_which), \
         patch("subprocess.run") as mock_run:
        # Mock active docker daemon check
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        cmd = get_contained_command(base_args, work_dir, clean_env)

        assert cmd[0] == "/usr/bin/docker"
        assert "run" in cmd
        assert "--net=none" in cmd
        assert "python:3.11-slim" in cmd
        assert cmd[-3] == "python3"  # translated python to python3
        assert cmd[-2] == "-m"
        assert cmd[-1] == "pytest"


def test_get_contained_command_docker_available_but_inactive_falls_back() -> None:
    """Verify that get_contained_command falls back to host execution if docker daemon is inactive."""
    base_args = ["python", "-m", "pytest"]
    work_dir = Path("/tmp/mock-repo")
    clean_env = {"PATH": "/usr/bin"}

    def mock_which(name: str) -> str | None:
        if name == "docker":
            return "/usr/bin/docker"
        return None

    with patch("shutil.which", side_effect=mock_which), \
         patch("subprocess.run") as mock_run:
        # Mock inactive/failed docker daemon check
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_run.return_value = mock_res

        cmd = get_contained_command(base_args, work_dir, clean_env)

        # Should fall back to host execution (original base_args)
        assert cmd == base_args


def test_get_contained_command_fallback() -> None:
    """Verify that get_contained_command returns base_args unmodified if neither bwrap nor docker is available."""
    base_args = ["python", "-m", "pytest"]
    work_dir = Path("/tmp/mock-repo")
    clean_env = {"PATH": "/usr/bin"}

    with patch("shutil.which", return_value=None):
        cmd = get_contained_command(base_args, work_dir, clean_env)
        assert cmd == base_args
