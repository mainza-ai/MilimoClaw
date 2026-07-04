# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Process Containment Sandboxing

Utility to wrap process invocations with bubblewrap or Docker for isolation.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("milimo.containment")


def get_contained_command(
    base_args: list[str],
    work_dir: Path | str,
    clean_env: dict[str, str],
) -> list[str]:
    """
    Wraps command arguments with bubblewrap or Docker containment if available.

    Args:
        base_args: Command list to run (e.g. [sys.executable, "-c", script] or ["python", "-m", "pytest"])
        work_dir: Directory where execution takes place and files must be mounted
        clean_env: Cleaned environment variables for subprocess execution

    Returns:
        Command list wrapped with containment utility, or base_args if none found.
    """
    bwrap_path = shutil.which("bwrap")
    docker_path = shutil.which("docker")
    work_dir_str = str(Path(work_dir).resolve())

    # Check if docker daemon is responsive
    is_docker_active = False
    if docker_path:
        try:
            proc_check = subprocess.run(
                [docker_path, "ps"],
                capture_output=True,
                timeout=2,
                env=clean_env,
            )
            if proc_check.returncode == 0:
                is_docker_active = True
        except Exception:
            pass

    if bwrap_path:
        cmd = [
            bwrap_path,
            "--unshare-all",
            "--proc", "/proc",
            "--dev", "/dev",
        ]
        # Bind-mount system binaries/libraries for execution
        for p in ["/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc"]:
            if os.path.exists(p):
                cmd += ["--ro-bind", p, p]
        # Bind-mount the working directory as read-write
        cmd += [
            "--bind", work_dir_str, work_dir_str,
            "--chdir", work_dir_str,
        ]
        cmd += base_args
        logger.info("Executing command under bubblewrap sandbox")
        return cmd
    elif is_docker_active and docker_path:
        # Wrap execution inside network-isolated Docker container
        cmd = [
            docker_path,
            "run",
            "--rm",
            "--net=none",
            "-v", f"{work_dir_str}:{work_dir_str}",
            "-w", work_dir_str,
            "python:3.11-slim",
        ]
        # Translate base_args. If starting with python/sys.executable, use python3
        translated_args = []
        for i, arg in enumerate(base_args):
            if i == 0 and (
                arg == "python"
                or arg == "python3"
                or arg == sys.executable
                or arg.endswith("/python")
                or arg.endswith("/python3")
            ):
                translated_args.append("python3")
            else:
                translated_args.append(arg)
        cmd += translated_args
        logger.info("Executing command under Docker sandbox")
        return cmd
    else:
        logger.warning("No bwrap or docker found; falling back to host subprocess execution")
        return base_args
