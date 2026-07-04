"""
War Room Bridge — file-system operations extracted from the HTTP request
handler so they can be tested, reused, and audited independently.

Endpoints that approve or veto messages delegate here to keep the handler
thin and focussed on HTTP concerns.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from milimo_core.contracts import VALID_RECIPIENTS

logger = logging.getLogger("milimo.warroom_bridge")


def resolve_mesh_dir() -> Path:
    candidates = [
        "/sandbox/.hermes/mesh",
        "/sandbox/.openclaw/milimo/mesh",
        "~/.openclaw/milimo/mesh",
        "~/.hermes/mesh",
        "./mesh",
    ]
    for raw in candidates:
        p = Path(raw).expanduser()
        if p.exists():
            return p
    p = Path(candidates[0]).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return p


def _safe_action_id(raw: str) -> str:
    if any(x in raw for x in ("/", "\\")) or raw.startswith("..") or raw.strip() in (".", ".."):
        raise ValueError(f"Invalid action_id: {raw!r}")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("action_id is empty")
    return cleaned


def approve_hold_message(action_id: str) -> Path:
    action_id = _safe_action_id(action_id)

    mesh_dir = resolve_mesh_dir()
    warroom_inbox = mesh_dir / "inbox" / "war_room"
    if not warroom_inbox.exists():
        raise RuntimeError("War Room inbox directory does not exist")

    target_file: Path | None = None
    msg_data: dict | None = None

    for candidate in sorted(warroom_inbox.glob("*.json"), key=lambda f: f.stat().st_mtime):
        if candidate.name == action_id or candidate.stem == action_id:
            target_file = candidate
            msg_data = json.loads(candidate.read_text(encoding="utf-8"))
            break

    if target_file is None or msg_data is None:
        raise RuntimeError(f"Action '{action_id}' not found in War Room hold queue")

    recipient = msg_data.get("recipient_role", "finance")
    if recipient not in VALID_RECIPIENTS:
        logger.warning(
            "Unexpected recipient_role %r in %s — falling back to 'finance'",
            recipient, action_id,
        )
        recipient = "finance"

    target_dir = mesh_dir / "inbox" / recipient
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.rename(target_dir / target_file.name)
    logger.info("Approved action %s: moved to %s", action_id, recipient)
    return target_file


def veto_hold_message(action_id: str) -> Path:
    action_id = _safe_action_id(action_id)

    mesh_dir = resolve_mesh_dir()
    warroom_inbox = mesh_dir / "inbox" / "war_room"
    if not warroom_inbox.exists():
        raise RuntimeError("War Room inbox directory does not exist")

    target_file: Path | None = None

    for candidate in sorted(warroom_inbox.glob("*.json"), key=lambda f: f.stat().st_mtime):
        if candidate.name == action_id or candidate.stem == action_id:
            target_file = candidate
            break

    if target_file is None:
        raise RuntimeError(f"Action '{action_id}' not found in War Room hold queue")

    rejected_dir = mesh_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    target_file.rename(rejected_dir / target_file.name)
    logger.info("Vetoed action %s: moved to rejected", action_id)
    return target_file
