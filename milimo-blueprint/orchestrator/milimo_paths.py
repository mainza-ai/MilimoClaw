# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Centralized path resolver for Milimo Claw data directories.

In a NemoClaw sandbox, the writable base directory is
/sandbox/.openclaw-data/milimo/ (NOT ~/.openclaw-data/milimo/ which varies by user).

All Python modules should use milimo_paths.MILIMO_DIR / "subdir"
instead of Path.home() / ".milimo" / "subdir".

Claw mount paths use CLAWS_DIR / <role> (e.g. /sandbox/.openclaw-data/milimo/claws/build)
because /sandbox/<role> is read-only under NemoClaw's Landlock policy.

IMPORTANT: MILIMO_DIR uses /sandbox/.openclaw-data/milimo/ (absolute) in sandbox mode,
not Path.home()/.openclaw-data/milimo/, because the launcher runs as root ($HOME=/root)
while the agent runs as sandbox ($HOME=/sandbox). Using Path.home() would cause the
launcher and agent to read/write to different directories.
"""

from __future__ import annotations

import os
from pathlib import Path

_SANDBOX_MILIMO_DIR = Path("/sandbox/.openclaw-data/milimo")
_HOME_MILIMO_DIR = Path.home() / ".openclaw-data" / "milimo"
_LEGACY_MILIMO_DIR = Path.home() / ".milimo"

_SANDBOX_CLAWS_BASE = Path("/sandbox/.openclaw-data/milimo/claws")
_LEGACY_CLAWS_BASE = Path("/sandbox")


def _is_sandbox() -> bool:
    return bool(os.environ.get("NEMOCLAW_MODEL")) or _SANDBOX_MILIMO_DIR.is_dir()


def _resolve_base() -> Path:
    """Return the primary Milimo data directory.

    In a NemoClaw sandbox: /sandbox/.openclaw-data/milimo/ (absolute, shared across users).
    Outside sandbox: ~/.openclaw-data/milimo/ or ~/.milimo/ for legacy.
    """
    if _is_sandbox():
        return _SANDBOX_MILIMO_DIR
    if _HOME_MILIMO_DIR.is_dir():
        return _HOME_MILIMO_DIR
    if _LEGACY_MILIMO_DIR.is_dir():
        return _LEGACY_MILIMO_DIR
    return _HOME_MILIMO_DIR


def _resolve_claws_base() -> Path:
    """Return the base directory for claw mount points.

    In a NemoClaw sandbox /sandbox/ is read-only (Landlock).
    Claw data directories live under /sandbox/.openclaw-data/milimo/claws/<role>.
    Falls back to /sandbox/<role> for non-sandbox environments.
    """
    if _is_sandbox() or _SANDBOX_CLAWS_BASE.is_dir():
        return _SANDBOX_CLAWS_BASE
    return _LEGACY_CLAWS_BASE


def claw_base(role: str) -> Path:
    """Return the mount path for a given claw role.

    Args:
        role: One of 'build', 'content', 'ops', 'analytics', 'finance', 'assistant'.

    Returns:
        Path like /sandbox/.openclaw-data/milimo/claws/build (sandbox)
        or /sandbox/build (non-sandbox).
    """
    return _resolve_claws_base() / role


MILIMO_DIR: Path = _resolve_base()
CLAWS_DIR: Path = _resolve_claws_base()
