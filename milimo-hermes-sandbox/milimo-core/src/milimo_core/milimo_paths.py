# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Centralized path resolver for Milimo Claw data directories.

In a NemoClaw sandbox under the OpenClaw profile, the writable base is
``/sandbox/.openclaw/milimo/``.

Under the **Hermes** profile (``MILIMO_PROFILE=hermes``) the base is
``/sandbox/.hermes/`` — consistent with Hermes' own config layout and
exposed to the host via ``scripts/hermes-sync.sh``.

All Python modules should use ``milimo_paths.MILIMO_DIR / "subdir"``
instead of ``Path.home() / ".milimo" / "subdir"``.

Claw mount paths use ``CLAWS_DIR / <role>`` (e.g.
``/sandbox/.hermes/claws/build`` for Hermes or
``/sandbox/.openclaw/milimo/claws/build`` for OpenClaw).

IMPORTANT: MILIMO_DIR always resolves to an absolute path in sandbox mode,
not ``Path.home()/.openclaw/milimo/``, because the launcher runs as root
(``$HOME=/root``) while the agent runs as sandbox (``$HOME=/sandbox``).
Using ``Path.home()`` would cause the launcher and agent to read/write to
different directories.

Profile resolution order:
1. ``MILIMO_PROFILE=hermes`` → ``/sandbox/.hermes/``
2. ``/sandbox/.openclaw/milimo/`` exists → OpenClaw sandbox
3. ``/sandbox/.openclaw-data/milimo/`` exists → legacy OpenClaw
4. ``NEMOCLAW_MODEL`` + ``/sandbox/`` exists → generic sandbox (default OpenClaw)
5. Host paths (``~/.openclaw/milimo/`` or legacy)
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Hermes profile paths ────────────────────────────────────────────────────
_HERMES_SANDBOX_DIR = Path("/sandbox/.hermes")
_HERMES_CLAWS_BASE = Path("/sandbox/.hermes/claws")

# ── OpenClaw profile paths ──────────────────────────────────────────────────
_SANDBOX_MILIMO_DIR = Path("/sandbox/.openclaw/milimo")
_HOME_MILIMO_DIR = Path.home() / ".openclaw" / "milimo"
_LEGACY_MILIMO_DIR = Path.home() / ".milimo"

_LEGACY_OPENCLAW_DATA_DIR = Path("/sandbox/.openclaw-data/milimo")
_LEGACY_HOME_OPENCLAW_DATA_DIR = Path.home() / ".openclaw-data" / "milimo"

_SANDBOX_CLAWS_BASE = Path("/sandbox/.openclaw/milimo/claws")
_LEGACY_CLAWS_BASE = Path("/sandbox")


def _is_hermes_profile() -> bool:
    """Return True when running under the Hermes profile.

    The environment variable ``MILIMO_PROFILE`` is set to ``hermes`` in the
    Hermes Dockerfile and is the canonical signal.
    """
    return os.environ.get("MILIMO_PROFILE") == "hermes"


def _is_sandbox() -> bool:
    """Detect if running inside a NemoClaw sandbox container.

    ``NEMOCLAW_MODEL`` alone is NOT sufficient — it is also set on the host
    when nemoclaw is configured.  We require the sandbox data directory
    to actually exist on the filesystem (or ``MILIMO_PROFILE=hermes``).
    """
    return (
        _is_hermes_profile()
        or _SANDBOX_MILIMO_DIR.is_dir()
        or _LEGACY_OPENCLAW_DATA_DIR.is_dir()
        or (bool(os.environ.get("NEMOCLAW_MODEL")) and Path("/sandbox").is_dir())
    )


def _resolve_base() -> Path:
    """Return the primary MilimoClaw data directory.

    Resolution order
    ----------------
    1. ``MILIMO_PROFILE=hermes`` → ``/sandbox/.hermes/``
    2. ``/sandbox/.openclaw/milimo/`` exists → OpenClaw sandbox
    3. ``/sandbox/.openclaw-data/milimo/`` exists → legacy OpenClaw
    4. Fallback OpenClaw sandbox ``/sandbox/.openclaw/milimo/``
    5. ``~/.openclaw/milimo/`` exists → host profile
    6. ``~/.openclaw-data/milimo/`` exists → legacy host
    7. ``~/.milimo/`` exists → legacy standalone
    8. Default ``~/.openclaw/milimo/``
    """
    # Hermes profile gets its own native base
    if _is_hermes_profile():
        return _HERMES_SANDBOX_DIR

    if _is_sandbox():
        if _SANDBOX_MILIMO_DIR.is_dir():
            return _SANDBOX_MILIMO_DIR
        if _LEGACY_OPENCLAW_DATA_DIR.is_dir():
            return _LEGACY_OPENCLAW_DATA_DIR
        return _SANDBOX_MILIMO_DIR

    if _HOME_MILIMO_DIR.is_dir():
        return _HOME_MILIMO_DIR
    if _LEGACY_HOME_OPENCLAW_DATA_DIR.is_dir():
        return _LEGACY_HOME_OPENCLAW_DATA_DIR
    if _LEGACY_MILIMO_DIR.is_dir():
        return _LEGACY_MILIMO_DIR
    return _HOME_MILIMO_DIR


def _resolve_claws_base() -> Path:
    """Return the base directory for claw mount points.

    Resolution order
    ----------------
    1. ``MILIMO_PROFILE=hermes`` → ``/sandbox/.hermes/claws/``
    2. ``/sandbox/.openclaw/milimo/claws/`` exists → OpenClaw sandbox
    3. ``/sandbox/.openclaw-data/milimo/claws/`` exists → legacy OpenClaw
    4. In sandbox (detected) → OpenClaw default
    5. Host → ``<resolved-base>/claws/``
    """
    if _is_hermes_profile():
        return _HERMES_CLAWS_BASE

    if _SANDBOX_CLAWS_BASE.is_dir():
        return _SANDBOX_CLAWS_BASE
    legacy_sandbox_claws = Path("/sandbox/.openclaw-data/milimo/claws")
    if legacy_sandbox_claws.is_dir():
        return legacy_sandbox_claws
    if _is_sandbox():
        return _SANDBOX_CLAWS_BASE
    return _resolve_base() / "claws"


def claw_base(role: str) -> Path:
    """Return the mount path for a given claw role.

    Args:
        role: One of 'build', 'content', 'ops', 'analytics', 'finance', 'assistant'.

    Returns:
        Path like /sandbox/.openclaw/milimo/claws/build (sandbox)
        or /sandbox/build (non-sandbox).
    """
    return _resolve_claws_base() / role


def config_path() -> Path:
    """Return the path to config.json, checking new location first, then legacy."""
    _candidates = [
        _resolve_base() / "config.json",
        _LEGACY_MILIMO_DIR / "config.json",
    ]
    return next((p for p in _candidates if p.exists()), _candidates[0])


def mesh_dir() -> Path:
    """Return the mesh directory (inbox, outbox, heartbeats, topology)."""
    return _resolve_base() / "mesh"


def health_dir(squad_id: str = "default") -> Path:
    """Return the health data directory for a squad."""
    return _resolve_base() / "health" / squad_id


def tools_dir(squad_id: str = "default", claw_role: str = "") -> Path:
    """Return the tool registry directory."""
    base = _resolve_base() / "tools" / squad_id
    if claw_role:
        return base / claw_role
    return base


def logs_dir(squad_id: str = "", claw_role: str = "") -> Path:
    """Return the logs directory."""
    base = _resolve_base() / "logs"
    if squad_id:
        base = base / squad_id
    if claw_role:
        base = base / claw_role
    return base


def state_dir() -> Path:
    """Return the state directory (deep work, etc.)."""
    return _resolve_base() / "state"


def keys_dir() -> Path:
    """Return the provenance keystore directory."""
    return _resolve_base() / "keys"


def blueprints_dir(squad_id: str = "", claw_role: str = "") -> Path:
    """Return the blueprints directory."""
    base = _resolve_base() / "blueprints"
    if squad_id:
        base = base / squad_id
    if claw_role:
        base = base / claw_role
    return base


def metrics_dir(claw_role: str = "") -> Path:
    """Return the metrics directory."""
    base = _resolve_base() / "metrics"
    if claw_role:
        base = base / claw_role
    return base


def marketplace_dir() -> Path:
    """Return the marketplace directory."""
    return _resolve_base() / "marketplace"


def latency_dir() -> Path:
    """Return the latency monitoring directory."""
    return _resolve_base() / "latency"


def cohorts_dir() -> Path:
    """Return the cohorts directory."""
    return _resolve_base() / "cohorts"


def attestations_dir() -> Path:
    """Return the attestations directory."""
    return _resolve_base() / "attestations"


def analytics_dir(subdir: str = "") -> Path:
    """Return the analytics data directory."""
    base = _resolve_base() / "analytics"
    if subdir:
        base = base / subdir
    return base


def inference_dir() -> Path:
    """Return the inference config directory."""
    return _resolve_base() / "inference"


def events_dir() -> Path:
    """Return the events directory (for realtime bridge)."""
    return _resolve_base() / "events"


def sandboxes_dir(role: str = "") -> Path:
    """Return the sandboxes directory (per-claw sandbox roots)."""
    base = _resolve_base() / "sandboxes"
    if role:
        base = base / role
    return base


MILIMO_DIR: Path = _resolve_base()
CLAWS_DIR: Path = _resolve_claws_base()
