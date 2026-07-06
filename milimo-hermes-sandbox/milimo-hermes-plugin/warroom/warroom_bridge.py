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
from typing import Any, Callable

from milimo_core.contracts import VALID_RECIPIENTS

logger = logging.getLogger("milimo.warroom_bridge")


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

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


def _warroom_inbox(mesh_dir: Path | None = None) -> Path:
    return (mesh_dir or resolve_mesh_dir()) / "inbox" / "war_room"


def _safe_action_id(raw: str) -> str:
    if any(x in raw for x in ("/", "\\")) or raw.startswith("..") or raw.strip() in (".", ".."):
        raise ValueError(f"Invalid action_id: {raw!r}")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("action_id is empty")
    return cleaned


# ---------------------------------------------------------------------------
# War room action file I/O (shared by all handlers and the TUI server)
# ---------------------------------------------------------------------------

def write_warroom_action(
    action_id: str,
    *,
    claw_role: str = "ops",
    mode: str = "REVIEW",
    action_type: str = "",
    summary: str = "",
    timestamp: str = "",
    recipient_role: str = "finance",
    payload: dict[str, Any] | None = None,
) -> Path:
    """Write a canonical War Room action file to mesh_dir/inbox/war_room/.

    All MilimoClaw handlers call this after creating an in-memory or
    filesystem-backed queue entry so that the TUI and Hermes agent share
    one source of truth.

    Returns the path of the written file.
    """
    mesh_dir = resolve_mesh_dir()
    inbox = _warroom_inbox(mesh_dir)
    inbox.mkdir(parents=True, exist_ok=True)

    action_id = _safe_action_id(action_id)
    data: dict[str, Any] = {
        "action_id": action_id,
        "message_id": action_id,
        "claw_role": claw_role,
        "mode": mode,
        "action_type": action_type or action_id,
        "summary": summary,
        "timestamp": timestamp or __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "recipient_role": recipient_role,
        "payload": payload or {},
    }
    target = inbox / f"{action_id}.json"
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.debug("Wrote war room action: %s", target)
    return target


def read_warroom_action(action_id: str) -> dict[str, Any] | None:
    """Return the parsed JSON dict for a war room file, or None if absent."""
    action_id = _safe_action_id(action_id)
    for candidate in _warroom_inbox().glob("*.json"):
        if candidate.name == action_id or candidate.stem == action_id:
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
    return None


def remove_warroom_action(action_id: str) -> bool:
    """Remove a war room file. Returns True if it was removed."""
    action_id = _safe_action_id(action_id)
    for candidate in _warroom_inbox().glob("*.json"):
        if candidate.name == action_id or candidate.stem == action_id:
            try:
                candidate.unlink()
                logger.debug("Removed war room action: %s", candidate)
                return True
            except OSError:
                return False
    return False


# ---------------------------------------------------------------------------
# Approve / Veto — with live handler dispatch
# ---------------------------------------------------------------------------

# Registered per recipient_role: {"on_approve": callable, "on_veto": callable}
_ACTION_HANDLERS: dict[str, dict[str, Callable]] = {}


def register_warroom_action_handler(
    role: str,
    on_approve: Callable[[str, dict[str, Any]], dict[str, Any] | None],
    on_veto: Callable[[str, dict[str, Any]], dict[str, Any] | None],
) -> None:
    """Register approve/veto callbacks for a recipient_role.

    Called by each claw's startup() so the TUI can dispatch approve/veto
    clicks without the Hermes agent.
    """
    _ACTION_HANDLERS[role] = {
        "on_approve": on_approve,
        "on_veto": on_veto,
    }
    logger.debug("Registered war room action handler for role=%s", role)


def approve_hold_message(action_id: str) -> Path:
    action_id = _safe_action_id(action_id)

    mesh_dir = resolve_mesh_dir()
    warroom_inbox = _warroom_inbox(mesh_dir)
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

    handler_entry = _ACTION_HANDLERS.get(recipient)
    if handler_entry:
        try:
            handler_entry["on_approve"](action_id, msg_data)
        except Exception:
            logger.exception(
                "[approve] handler error for %s (role=%s)", action_id, recipient
            )

    logger.info("Approved action %s: moved to %s", action_id, recipient)
    # file is already in inbox/{recipient}; remove war_room ref if any duplicate
    war_room_copy = warroom_inbox / f"{action_id}.json"
    if war_room_copy.exists():
        try:
            war_room_copy.unlink()
        except OSError:
            pass
    return target_file


def veto_hold_message(action_id: str) -> Path:
    action_id = _safe_action_id(action_id)

    mesh_dir = resolve_mesh_dir()
    warroom_inbox = _warroom_inbox(mesh_dir)
    if not warroom_inbox.exists():
        raise RuntimeError("War Room inbox directory does not exist")

    target_file: Path | None = None
    msg_data: dict | None = None

    for candidate in sorted(warroom_inbox.glob("*.json"), key=lambda f: f.stat().st_mtime):
        if candidate.name == action_id or candidate.stem == action_id:
            target_file = candidate
            msg_data = json.loads(candidate.read_text(encoding="utf-8"))
            break

    if target_file is None:
        raise RuntimeError(f"Action '{action_id}' not found in War Room hold queue")

    # Determine recipient_role so we can also dispatch to their veto callback
    recipient = msg_data.get("recipient_role", "finance") if msg_data else "finance"
    if recipient not in VALID_RECIPIENTS:
        recipient = "finance"

    rejected_dir = mesh_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    target_file.rename(rejected_dir / target_file.name)

    handler_entry = _ACTION_HANDLERS.get(recipient)
    if handler_entry:
        try:
            handler_entry["on_veto"](action_id, msg_data or {})
        except Exception:
            logger.exception(
                "[veto] handler error for %s (role=%s)", action_id, recipient
            )

    logger.info("Vetoed action %s: moved to rejected", action_id)
    return target_file
