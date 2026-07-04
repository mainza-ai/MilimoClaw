# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Bridge CLI

A proper CLI entry point for TypeScript → Python communication.
Accepts structured JSON input and returns structured JSON output.

Usage:
    python3 bridge_cli.py --command evolution_status --args '{"claw": "build"}'

Response format:
    {"success": true, "data": {...}}
    {"success": false, "error": "error message"}

All output goes to stdout. Debug logs go to stderr only.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone
from orchestrator.milimo_paths import (
    CLAWS_DIR,
    config_path,
    claw_base,
    mesh_dir as milimo_mesh_dir,
    health_dir,
    tools_dir,
    logs_dir,
    blueprints_dir,
    state_dir,
)

# Configure logging to stderr only
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("milimo.bridge_cli")

# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------


def _read_evolution_summary() -> dict[str, Any]:
    """Read the lightweight evolution summary file without importing the scheduler."""
    summary_path = state_dir() / "evolution" / "summary.json"
    if not summary_path.exists():
        return {}
    try:
        return json.loads(summary_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _query_evolution_status(squad_id: str, claw_role: str) -> dict[str, Any]:
    """Query evolution status from persisted state — no scheduler import needed."""
    summary = _read_evolution_summary()
    by_role = summary.get("by_role", {})
    role_data = by_role.get(claw_role, {})

    registry_file = claw_base(claw_role) / "sandbox" / "tools" / "registry.json"
    tools: dict[str, Any] = {}
    if registry_file.exists():
        try:
            tools = json.loads(registry_file.read_text()).get("tools", {})
        except (json.JSONDecodeError, OSError):
            pass

    has_ever_run = claw_role in by_role
    last_run = role_data.get("last_run")
    last_stage = role_data.get("last_stage")
    tools_deployed = role_data.get("tools_deployed", 0)

    if last_stage == "deploy":
        status = "success"
    elif last_stage == "error":
        status = "error"
    elif last_stage is not None:
        status = "incomplete"
    elif not has_ever_run:
        status = "never_run"
    else:
        status = "unknown"

    return {
        "status": status,
        "last_cycle": last_run,
        "last_stage_reached": last_stage,
        "last_skipped_reason": role_data.get("last_skipped_reason"),
        "tools_deployed": tools_deployed,
        "tool_count": len(tools),
        "evolution_ever_run": has_ever_run,
        "diagnostic_note": (
            "Evolution cycle has never run on this claw"
            if not has_ever_run
            else f"Last cycle reached '{last_stage}' on {last_run}"
            if last_run
            else None
        ),
    }


def handle_evolution_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get evolution status for a specific claw."""
    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw", "content")
    return _query_evolution_status(squad_id, claw_role)


def handle_blueprint_info(args: dict[str, Any]) -> dict[str, Any]:
    """Get blueprint information."""
    from pathlib import Path

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")

    # Check if blueprint_dir exists
    blueprint_path = Path(blueprint_dir)
    if not blueprint_path.exists():
        raise RuntimeError(f"Blueprint directory does not exist: {blueprint_dir}")

    try:
        from orchestrator.blueprint_manager import BlueprintManager

        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        current_version = mgr.current_version()
        snapshot = mgr._load_snapshot(current_version)

        tools_inventory = getattr(snapshot, "tools_inventory", None) or {}
        integrity = getattr(snapshot, "integrity", None) or {}

        return {
            "version": current_version,
            "squad_id": squad_id,
            "claw_role": claw_role,
            "tools_count": len(tools_inventory),
            "has_attestation": "attestation" in integrity,
        }
    except Exception as e:
        logger.exception("Failed to get blueprint info")
        raise RuntimeError(f"Blueprint info error: {e}") from e


def handle_blueprint_list(args: dict[str, Any]) -> dict[str, Any]:
    """List available blueprints."""
    from orchestrator.blueprint_manager import BlueprintManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")

    try:
        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        versions = mgr.list_versions()
        current = mgr.current_version()

        return {
            "versions": versions,
            "current_version": current,
            "total_versions": len(versions),
        }
    except Exception as e:
        logger.exception("Failed to list blueprints")
        raise RuntimeError(f"Blueprint list error: {e}") from e


def handle_blueprint_diff(args: dict[str, Any]) -> dict[str, Any]:
    """Get diff between two blueprint versions."""
    from orchestrator.blueprint_manager import BlueprintManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")
    version_a = args.get("version_a", "0.1.0")
    version_b = args.get("version_b", "0.2.0")

    try:
        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        diff = mgr.diff(version_a, version_b)

        return {
            "tools_added": diff.tools_added,
            "tools_removed": diff.tools_removed,
            "tools_modified": diff.tools_modified,
            "policy_changes": diff.policy_changes,
            "config_changes": diff.config_changes,
        }
    except Exception as e:
        logger.exception("Failed to diff blueprints")
        raise RuntimeError(f"Blueprint diff error: {e}") from e


def handle_blueprint_export(args: dict[str, Any]) -> dict[str, Any]:
    """Export blueprint snapshot."""
    from orchestrator.blueprint_manager import BlueprintManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")

    try:
        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        snapshot = mgr.export()
        return snapshot.to_dict()
    except Exception as e:
        logger.exception("Failed to export blueprint")
        raise RuntimeError(f"Blueprint export error: {e}") from e


def handle_blueprint_rollback(args: dict[str, Any]) -> dict[str, Any]:
    """Rollback blueprint to a specific version."""
    from orchestrator.blueprint_manager import BlueprintManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")
    target_version = args.get("target_version", "")
    reason = args.get("reason", "")

    try:
        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        success = mgr.rollback(target_version, reason)
        return {"success": success, "version": target_version}
    except Exception as e:
        logger.exception("Failed to rollback blueprint")
        raise RuntimeError(f"Blueprint rollback error: {e}") from e


def handle_tool_registry(args: dict[str, Any]) -> dict[str, Any]:
    """Get tool registry inventory."""
    from orchestrator.tool_registry import ToolRegistry

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")

    try:
        registry = ToolRegistry(squad_id, claw_role)
        inventory = registry.get_inventory()
        return {
            "tools": inventory,
            "count": len(inventory),
        }
    except Exception as e:
        logger.exception("Failed to get tool registry")
        raise RuntimeError(f"Tool registry error: {e}") from e


def handle_marketplace_search(args: dict[str, Any]) -> dict[str, Any]:
    """Search marketplace for blueprints."""
    from orchestrator.marketplace_manager import MarketplaceManager

    query = args.get("query", "")
    category = args.get("category", "")

    try:
        market = MarketplaceManager()
        results = market.search(query, category)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.exception("Failed to search marketplace")
        raise RuntimeError(f"Marketplace search error: {e}") from e


def handle_marketplace_download(args: dict[str, Any]) -> dict[str, Any]:
    """Download a blueprint from marketplace."""
    from orchestrator.marketplace_manager import MarketplaceManager

    blueprint_id = args.get("blueprint_id", "")

    try:
        market = MarketplaceManager()
        snapshot = market.download(blueprint_id)
        if snapshot:
            return {"success": True, "snapshot": snapshot.to_dict()}
        return {"success": False, "error": "Blueprint not found"}
    except Exception as e:
        logger.exception("Failed to download from marketplace")
        raise RuntimeError(f"Marketplace download error: {e}") from e


def handle_marketplace_publish(args: dict[str, Any]) -> dict[str, Any]:
    """Publish a blueprint to marketplace."""
    from orchestrator.blueprint_manager import BlueprintManager
    from orchestrator.marketplace_manager import MarketplaceManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")
    price = args.get("price", "free")
    display_name = args.get("display_name", "")
    author = args.get("author", "")

    try:
        mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
        market = MarketplaceManager()
        snapshot = mgr.export()
        blueprint_id = market.publish(snapshot, price, display_name, author)
        return {"success": True, "blueprint_id": blueprint_id}
    except Exception as e:
        logger.exception("Failed to publish to marketplace")
        raise RuntimeError(f"Marketplace publish error: {e}") from e


def handle_mesh_flow_state(args: dict[str, Any]) -> dict[str, Any]:
    """Get cross-claw mesh signal flow state — live topology and pending messages."""

    _squad_id = args.get("squad", "default")

    try:
        _mesh_dir = milimo_mesh_dir()
        topology_file = _mesh_dir / "topology.json"

        # Load live topology
        nodes: dict[str, Any] = {}
        if topology_file.exists():
            try:
                topo_data = json.loads(topology_file.read_text())
                nodes = topo_data.get("nodes", {})
            except (json.JSONDecodeError, OSError):
                pass

        # Count pending messages per claw
        pending_counts: dict[str, int] = {}
        total_pending = 0
        if (_mesh_dir / "inbox").exists():
            for claw_dir in (_mesh_dir / "inbox").iterdir():
                if claw_dir.is_dir():
                    count = len(list(claw_dir.glob("*.json")))
                    pending_counts[claw_dir.name] = count
                    total_pending += count

        # Count delivered messages this week
        delivered_this_week = 0
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        if (_mesh_dir / "delivered").exists():
            for msg_file in (_mesh_dir / "delivered").glob("*.json"):
                try:
                    data = json.loads(msg_file.read_text())
                    ts = data.get("timestamp", "")
                    if ts:
                        msg_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if msg_dt > week_ago:
                            delivered_this_week += 1
                except (json.JSONDecodeError, OSError, ValueError):
                    pass

        # Build node status summary
        node_summaries = {}
        for role, node_data in nodes.items():
            node_summaries[role] = {
                "status": node_data.get("status", "unknown"),
                "address": node_data.get("address", ""),
                "last_heartbeat": node_data.get("last_heartbeat"),
                "pending_messages": pending_counts.get(role, 0),
            }

        return {
            "nodes": node_summaries,
            "total_pending": total_pending,
            "delivered_this_week": delivered_this_week,
            "pending_by_claw": pending_counts,
            "transport_mode": "file",  # Default; read from config if available
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to get mesh flow state")
        raise RuntimeError(f"Mesh flow state error: {e}") from e


def handle_health_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get health status for claws."""
    squad_id = args.get("squad_id", "default")

    try:
        import json

        _health_dir = health_dir(squad_id)
        if not _health_dir.exists():
            return {}
        status = {}
        for f in _health_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                claw = f.stem
                status[claw] = data
            except Exception:
                pass
        return status
    except Exception as e:
        logger.exception("Failed to get health status")
        raise RuntimeError(f"Health status error: {e}") from e


def handle_provenance_verify(args: dict[str, Any]) -> dict[str, Any]:
    """Verify blueprint provenance."""
    from orchestrator.provenance_verifier import ProvenanceVerifier
    from orchestrator.provenance_signer import Attestation

    blueprint_dir = args.get("blueprint_dir", ".")
    version = args.get("version", "latest")
    strict = args.get("strict", False)
    _squad_id = args.get("squad_id", "default")
    _claw_role = args.get("claw_role", "content")

    try:
        verifier = ProvenanceVerifier(strict_mode=strict)
        # Load attestation from blueprint
        version_file = Path(blueprint_dir) / "versions" / f"v{version}.json"
        if not version_file.exists():
            return {"valid": False, "errors": ["Version file not found"]}

        data = json.loads(version_file.read_text())
        attestation_data = data.get("integrity", {}).get("attestation", {})
        if not attestation_data:
            return {"valid": False, "errors": ["No attestation found"]}

        attestation = Attestation.from_dict(attestation_data)
        result = verifier.verify(attestation)
        return result.to_dict()
    except Exception as e:
        logger.exception("Failed to verify provenance")
        raise RuntimeError(f"Provenance verify error: {e}") from e


def handle_provenance_keygen(args: dict[str, Any]) -> dict[str, Any]:
    """Generate provenance signing key pair."""
    from orchestrator.provenance_signer import generate_key_pair, save_key_pair

    squad_id = args.get("squad", "default")

    try:
        private_key, public_key = generate_key_pair()
        key_file = save_key_pair(squad_id, private_key, public_key)
        return {
            "success": True,
            "key_file": str(key_file),
            "public_key": public_key.hex(),
            "key_id": public_key[:8].hex(),
        }
    except Exception as e:
        logger.exception("Failed to generate key pair")
        raise RuntimeError(f"Provenance keygen error: {e}") from e


def handle_revenue_summary(args: dict[str, Any]) -> dict[str, Any]:
    """Get revenue summary for War Room widget."""
    from orchestrator.solo_warroom import SoloWarRoom
    from pathlib import Path

    _squad_id = args.get("squad_id", "default")
    sandbox_dir = args.get("sandbox_dir")

    try:
        config = {"war_room": {"operator": "operator", "mode": "solo"}}
        warroom = SoloWarRoom(config)

        sandbox_path = Path(sandbox_dir) if sandbox_dir else None
        summary = warroom.get_revenue_summary(sandbox_path)

        return {
            "week_revenue": summary.week_revenue,
            "week_over_week_pct": summary.week_over_week_pct,
            "invoices_paid": summary.invoices_paid,
            "invoices_pending": summary.invoices_pending,
            "last_updated": summary.last_updated,
        }
    except Exception as e:
        logger.exception("Failed to get revenue summary")
        raise RuntimeError(f"Revenue summary error: {e}") from e


def handle_morning_brief(args: dict[str, Any]) -> dict[str, Any]:
    """Generate morning brief digest."""
    from orchestrator.solo_warroom import SoloWarRoom

    _squad_id = args.get("squad_id", "default")

    try:
        config = {"war_room": {"operator": "operator", "mode": "solo"}}
        warroom = SoloWarRoom(config)

        stats = warroom.get_stats()
        pending = warroom.get_pending()

        return {
            "overnight_actions": stats.get("auto_executed_today", 0),
            "queue_summary": {
                "hold": stats.get("hold_count", 0),
                "review": stats.get("review_count", 0),
                "auto": stats.get("auto_count", 0),
            },
            "pending_actions": [
                {
                    "id": a.id,
                    "claw": a.claw,
                    "type": a.action_type,
                    "priority": a.priority.name,
                }
                for a in pending[:10]
            ],
        }
    except Exception as e:
        logger.exception("Failed to generate morning brief")
        raise RuntimeError(f"Morning brief error: {e}") from e


def handle_evening_wrap(args: dict[str, Any]) -> dict[str, Any]:
    """Generate evening wrap digest."""
    from orchestrator.solo_warroom import SoloWarRoom

    _squad_id = args.get("squad_id", "default")

    try:
        config = {"war_room": {"operator": "operator", "mode": "solo"}}
        warroom = SoloWarRoom(config)

        stats = warroom.get_stats()

        return {
            "today_completed": stats.get("processed_today", 0),
            "auto_executed": stats.get("auto_executed_today", 0),
            "remaining_pending": stats.get("total_pending", 0),
        }
    except Exception as e:
        logger.exception("Failed to generate evening wrap")
        raise RuntimeError(f"Evening wrap error: {e}") from e


def handle_activate_deep_work(args: dict[str, Any]) -> dict[str, Any]:
    """Activate deep work mode."""
    from orchestrator.solo_deep_work import activate_deep_work_mode

    resume_date = args.get("resume_date", "")
    if not resume_date:
        raise RuntimeError("resume_date is required")

    try:
        config = {"war_room": {"operator": "operator", "mode": "solo"}}
        result = activate_deep_work_mode(config, resume_date, quiet=True)
        return result
    except ValueError as e:
        raise RuntimeError(str(e)) from e
    except Exception as e:
        logger.exception("Failed to activate deep work mode")
        raise RuntimeError(f"Activate deep work error: {e}") from e


def handle_resume_deep_work(args: dict[str, Any]) -> dict[str, Any]:
    """Resume from deep work mode."""
    from orchestrator.solo_deep_work import deactivate_deep_work_mode

    try:
        config = {"war_room": {"operator": "operator", "mode": "solo"}}
        result = deactivate_deep_work_mode(config, quiet=True)
        return result
    except Exception as e:
        logger.exception("Failed to resume from deep work mode")
        raise RuntimeError(f"Resume deep work error: {e}") from e


def handle_deep_work_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get deep work mode status."""
    from orchestrator.solo_deep_work import get_deep_work_status

    try:
        result = get_deep_work_status()
        return result
    except Exception as e:
        logger.exception("Failed to get deep work status")
        raise RuntimeError(f"Deep work status error: {e}") from e


def handle_collect_health(args: dict[str, Any]) -> dict[str, Any]:
    """Collect health data for all claws."""
    squad_id = args.get("squad_id", "default")

    try:
        result: dict[str, Any] = {}
        claw_roles = ["content", "ops", "analytics", "finance", "build", "assistant"]

        for role in claw_roles:
            claw_health = _collect_claw_health(role, squad_id)
            result[role] = claw_health

        return result
    except Exception as e:
        logger.exception("Failed to collect health data")
        raise RuntimeError(f"Collect health error: {e}") from e


MILIMO_CONFIG_PATH = config_path()


def handle_squad_config(args: dict[str, Any]) -> dict[str, Any]:
    """Get squad configuration (credentials stripped)."""
    try:
        if not MILIMO_CONFIG_PATH.exists():
            return {"error": "config not found", "data_quality": "missing"}

        config = json.loads(MILIMO_CONFIG_PATH.read_text(encoding="utf-8"))

        # Strip credential fields
        STRIP_KEYS = {
            "stripe_key",
            "github_token",
            "api_key",
            "secret",
            "credentials",
            "meshSecret",
        }
        safe_config = {k: v for k, v in config.items() if k not in STRIP_KEYS}

        assistant = config.get("assistant", {})

        return {
            "config": safe_config,
            "assistant_name": assistant.get("name", "unknown"),
            "assistant_emoji": assistant.get("emoji", "🦀"),
            "active_claws": config.get("activeClaws", []),
            "data_quality": "complete",
        }
    except Exception as e:
        logger.exception("Failed to get squad config")
        raise RuntimeError(f"Squad config error: {e}") from e


def _collect_claw_health(role: str, squad_id: str) -> dict[str, Any]:
    """Collect health for a single claw."""
    _now = datetime.now(timezone.utc).isoformat()

    claw_health: dict[str, Any] = {
        "role": role,
        "status": "idle",
        "tool_count": 0,
        "last_evolution": None,
        "last_action": None,
        "actions_this_week": 0,
        "sparkline": [0, 0, 0, 0, 0, 0, 0],
    }

    registry_path = tools_dir(squad_id, role) / "registry.json"
    if registry_path.exists():
        try:
            data = json.loads(registry_path.read_text())
            tools = data.get("tools", {})
            claw_health["tool_count"] = len(tools)

            last_evo = data.get("last_evolution")
            if last_evo:
                claw_health["last_evolution"] = last_evo
        except Exception:
            pass

    warroom_log = logs_dir() / "warroom.log"
    if warroom_log.exists():
        try:
            claw_health["last_action"] = _get_last_action_time(role, warroom_log)
            claw_health["actions_this_week"] = _count_actions_this_week(
                role, warroom_log
            )
            claw_health["sparkline"] = _calculate_sparkline(role, warroom_log)
        except Exception:
            pass

    pending_dir = milimo_mesh_dir() / "queue" / "pending"
    if pending_dir.exists():
        pending_hold = 0
        pending_review = 0
        for msg_file in pending_dir.glob("*.json"):
            try:
                msg = json.loads(msg_file.read_text())
                if msg.get("sender_role") == role:
                    if msg.get("priority") == "HOLD":
                        pending_hold += 1
                    elif msg.get("priority") == "REVIEW":
                        pending_review += 1
            except Exception:
                pass

        if pending_hold > 0:
            claw_health["status"] = "processing"
        elif claw_health["last_action"]:
            try:
                last_action_dt = datetime.fromisoformat(claw_health["last_action"])
                if (datetime.now(timezone.utc) - last_action_dt).total_seconds() < 60:
                    claw_health["status"] = "active"
            except Exception:
                pass

    return claw_health


def _get_last_action_time(role: str, log_file: Path) -> str | None:
    """Get the last action timestamp for a claw from the log."""
    try:
        lines = log_file.read_text().splitlines()
        for line in reversed(lines[-100:]):
            if f"claw={role}" in line or f"from {role}" in line:
                parts = line.split(" - ")
                if parts:
                    timestamp_str = parts[0]
                    try:
                        dt = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        )
                        return dt.isoformat()
                    except Exception:
                        pass
    except Exception:
        pass
    return None


def _count_actions_this_week(role: str, log_file: Path) -> int:
    """Count actions for a claw in the last 7 days."""
    try:
        lines = log_file.read_text().splitlines()
        count = 0
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        for line in lines[-1000:]:
            if f"claw={role}" in line or f"from {role}" in line:
                parts = line.split(" - ")
                if parts:
                    try:
                        dt = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
                        if dt > week_ago:
                            count += 1
                    except Exception:
                        pass
        return count
    except Exception:
        return 0


def _calculate_sparkline(role: str, log_file: Path) -> list[int]:
    """Calculate 7-day sparkline for a claw."""
    try:
        lines = log_file.read_text().splitlines()
        sparkline: list[int] = [0, 0, 0, 0, 0, 0, 0]
        today = datetime.now(timezone.utc).date()

        for line in lines[-5000:]:
            if f"claw={role}" in line or f"from {role}" in line:
                parts = line.split(" - ")
                if parts:
                    try:
                        dt = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
                        days_ago = (today - dt.date()).days
                        if 0 <= days_ago < 7:
                            sparkline[6 - days_ago] += 1
                    except Exception:
                        pass
        return sparkline
    except Exception:
        return [0, 0, 0, 0, 0, 0, 0]


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------


def handle_send_to_claw(args: dict[str, Any]) -> dict[str, Any]:
    """Send a typed message from the assistant to a specific claw via the mesh.

    The assistant (Lucy) uses this to instruct or query claws. All messages
    are sent with REVIEW priority so the operator must approve before the
    claw acts on them.

    Args:
        role: Recipient claw role (content, ops, analytics, finance, build, assistant)
        type: Message type (assistant_query, assistant_task)
        payload: Message payload
        squad_id: Squad ID (default: "default")
        wait_for_result: If True, wait up to 60s for result (default: False)
        result_timeout: Max seconds to wait for result (default: 60)

    Returns:
        Dict with delivery status and optional result if wait_for_result=True
    """
    import time

    from orchestrator.contracts import (
        ClawMessage,
        VALID_SENDERS,
        VALID_RECIPIENTS,
        VALID_MESSAGE_TYPES,
        ASSISTANT_ROLE,
    )
    from orchestrator.mesh import MeshCoordinator

    recipient_role = args.get("role", "")
    message_type = (
        args.get("type") or args.get("message_type") or args.get("message_types") or ""
    )
    payload = args.get("payload", {})
    squad_id = args.get("squad_id", "default")
    wait_for_result = args.get("wait_for_result", False)
    result_timeout = args.get("result_timeout", 60)

    if not recipient_role:
        raise RuntimeError(
            "role is required (e.g., 'content', 'ops', 'analytics', 'finance', 'build', 'assistant')"
        )
    if not message_type:
        raise RuntimeError(
            "type is required (e.g., 'assistant_query', 'assistant_task')"
        )

    # Validate inputs
    if ASSISTANT_ROLE not in VALID_SENDERS:
        raise RuntimeError("Assistant role not configured as valid sender")
    if recipient_role not in VALID_RECIPIENTS:
        raise RuntimeError(f"Invalid recipient role: {recipient_role}")
    if message_type not in VALID_MESSAGE_TYPES:
        raise RuntimeError(f"Invalid message type: {message_type}")

    # Build the message
    message = ClawMessage(
        sender_role=ASSISTANT_ROLE,
        recipient_role=recipient_role,
        message_type=message_type,
        payload=payload,
        squad_id=squad_id,
    )

    # Route through MeshCoordinator using the real mesh config
    _mesh_dir = milimo_mesh_dir()
    config_path = Path(__file__).parent.parent / "mesh_config.yaml"
    if config_path.exists():
        mesh = MeshCoordinator.from_config_file(
            str(config_path), squad_id=squad_id, mesh_dir=str(_mesh_dir)
        )
    else:
        mesh = MeshCoordinator.from_dict({}, squad_id=squad_id, mesh_dir=str(_mesh_dir))

    # Register all known claws so the mesh knows who exists
    for claw_role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        mesh.register_claw(claw_role, address=f"local://{claw_role}")

    result = mesh.send_message(message)

    response = {
        "delivered": result.delivered,
        "message_id": result.message_id,
        "reason": result.reason,
        "requires_approval": result.requires_approval,
        "recipient": recipient_role,
        "message_type": message_type,
    }

    if wait_for_result and result.delivered:
        start_time = time.time()
        while time.time() - start_time < result_timeout:
            result_data = handle_get_result(
                {
                    "message_id": result.message_id,
                    "role": recipient_role,
                }
            )
            if result_data.get("status") == "found":
                response["result"] = result_data.get("result")
                response["result_status"] = "complete"
                return response
            time.sleep(2)

        response["result_status"] = "timeout"
        response["result_message"] = f"No result after {result_timeout}s"

    return response


def handle_claw_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get detailed status of a specific claw by reading its sandbox and health data."""
    squad_id = args.get("squad_id", "default")
    claw_role = args.get("role", "")

    if not claw_role:
        raise RuntimeError("role is required")
    if claw_role not in {
        "content",
        "ops",
        "analytics",
        "finance",
        "build",
        "assistant",
    }:
        raise RuntimeError(f"Invalid claw role: {claw_role}")

    result: dict[str, Any] = {"role": claw_role}

    health_file = health_dir(squad_id) / "health.json"
    if health_file.exists():
        try:
            data = json.loads(health_file.read_text())
            claw_health = data.get("claws", {}).get(claw_role, {})
            result["health"] = (
                claw_health if claw_health else {"status": "no_health_data"}
            )
        except (json.JSONDecodeError, OSError):
            result["health"] = {
                "status": "unknown",
                "error": "failed to read health file",
            }
    else:
        result["health"] = {"status": "no_health_data"}

    # Read tool registry
    registry_file = claw_base(claw_role) / "sandbox" / "tools" / "registry.json"
    if registry_file.exists():
        try:
            reg_data = json.loads(registry_file.read_text())
            tools = reg_data.get("tools", {})
            result["tool_count"] = len(tools)
            result["last_evolution"] = reg_data.get("last_evolution")
        except (json.JSONDecodeError, OSError):
            result["tool_count"] = 0
    else:
        result["tool_count"] = 0

    # Evolution status from summary.json
    evo = _query_evolution_status(squad_id, claw_role)
    result["evolution_status"] = evo.get("status", "never_run")
    result["evolution_ever_run"] = evo.get("evolution_ever_run", False)

    # Interpretation metadata
    result["tool_count_interpretation"] = (
        "Tools are registered by the weekly evolution cycle; 0 tools means evolution has not yet run"
        if result["tool_count"] == 0
        else f"{result['tool_count']} tool(s) registered via evolution cycle"
    )
    result["health_interpretation"] = (
        "No health data collected yet — health collector may not be running"
        if result["health"].get("status") == "no_health_data"
        else f"Health score: {result['health'].get('score', 'unknown')}"
    )
    result["diagnostic_note"] = evo.get("diagnostic_note")

    # Read pending messages for this claw
    _mesh_dir = milimo_mesh_dir()
    inbox = _mesh_dir / "inbox" / claw_role
    if inbox.exists():
        pending = []
        for msg_file in sorted(inbox.glob("*.json")):
            try:
                msg = json.loads(msg_file.read_text())
                pending.append(
                    {
                        "message_id": msg.get("message_id"),
                        "sender": msg.get("sender_role"),
                        "type": msg.get("message_type"),
                        "timestamp": msg.get("timestamp"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                pass
        result["pending_messages"] = pending
    else:
        result["pending_messages"] = []

    # Read sandbox status (check if sandbox directory exists)
    sandbox_path = CLAWS_DIR / claw_role
    result["sandbox_exists"] = sandbox_path.exists()
    if sandbox_path.exists():
        try:
            result["sandbox_contents"] = [
                d.name for d in sandbox_path.iterdir() if d.is_dir()
            ]
        except OSError:
            result["sandbox_contents"] = []

    return result


def handle_ops_active_projects(args: dict[str, Any]) -> dict[str, Any]:
    """List active client projects from the Ops claw sandbox."""
    sandbox = claw_base("ops")
    result: dict[str, Any] = {"projects": [], "sandbox_exists": sandbox.exists()}

    if not sandbox.exists():
        result["note"] = (
            "Ops sandbox not initialized. Run build_init to create /sandbox/clients/"
        )
        return result

    # Look for client/project files
    for client_dir in sorted(sandbox.iterdir()):
        if client_dir.is_dir():
            client_data: dict[str, Any] = {"name": client_dir.name, "projects": []}
            for project_file in client_dir.glob("*.json"):
                try:
                    data = json.loads(project_file.read_text())
                    client_data["projects"].append(
                        {
                            "id": data.get("project_id", project_file.stem),
                            "status": data.get("status", "unknown"),
                            "client_id": data.get("client_id"),
                        }
                    )
                except (json.JSONDecodeError, OSError):
                    pass
            result["projects"].append(client_data)

    # Also check for flat project files
    for project_file in sorted(sandbox.glob("*.json")):
        try:
            data = json.loads(project_file.read_text())
            result["projects"].append(
                {
                    "id": data.get("project_id", project_file.stem),
                    "status": data.get("status", "unknown"),
                    "client_id": data.get("client_id"),
                }
            )
        except (json.JSONDecodeError, OSError):
            pass

    return result


def handle_content_pending_drafts(args: dict[str, Any]) -> dict[str, Any]:
    """List pending content drafts from the Content claw sandbox."""
    sandbox = claw_base("content")
    result: dict[str, Any] = {"drafts": [], "sandbox_exists": sandbox.exists()}

    if not sandbox.exists():
        result["note"] = "Content sandbox not initialized."
        return result

    # Check data directory for draft files
    data_dir = sandbox / "data"
    if data_dir.exists():
        for draft_file in sorted(data_dir.glob("*.json")):
            try:
                data = json.loads(draft_file.read_text())
                result["drafts"].append(
                    {
                        "id": data.get("draft_id", draft_file.stem),
                        "status": data.get("status", "unknown"),
                        "platform": data.get("platform"),
                        "content_type": data.get("content_type"),
                        "client_id": data.get("client_id"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                pass

    # Also check for draft files directly in sandbox
    for draft_file in sorted(sandbox.glob("*.json")):
        try:
            data = json.loads(draft_file.read_text())
            if (
                "draft" in draft_file.stem.lower()
                or "content" in draft_file.stem.lower()
            ):
                result["drafts"].append(
                    {
                        "id": data.get("draft_id", draft_file.stem),
                        "status": data.get("status", "unknown"),
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass

    return result


def handle_build_open_prs(args: dict[str, Any]) -> dict[str, Any]:
    """List open PRs from the Build claw using the gh CLI."""
    import subprocess

    result: dict[str, Any] = {"prs": [], "gh_available": False}

    # Check if gh CLI is available
    try:
        gh_check = subprocess.run(
            ["gh", "--version"], capture_output=True, text=True, timeout=5
        )
        result["gh_available"] = gh_check.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        result["gh_available"] = False
        result["note"] = "gh CLI not available. Install with: brew install gh"
        return result

    # Fetch open PRs
    try:
        pr_output = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,title,author,createdAt,updatedAt,labels,url",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if pr_output.returncode == 0:
            result["prs"] = json.loads(pr_output.stdout)
        else:
            result["error"] = pr_output.stderr.strip()
    except subprocess.TimeoutExpired:
        result["error"] = "gh pr list timed out"
    except (json.JSONDecodeError, OSError) as e:
        result["error"] = str(e)

    return result


def handle_analytics_latest_report_summary(args: dict[str, Any]) -> dict[str, Any]:
    """Summarize the latest intelligence report from the Analytics claw."""
    reports_dir = claw_base("analytics") / "reports"
    result: dict[str, Any] = {
        "report": None,
        "reports_found": [],
        "reports_dir_exists": reports_dir.exists(),
    }

    if not reports_dir.exists():
        result["note"] = "Analytics reports directory not found."
        return result

    # Find the latest report files
    report_files = sorted(
        reports_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
    )

    for rf in report_files[:10]:
        result["reports_found"].append(
            {
                "filename": rf.name,
                "modified": datetime.fromtimestamp(
                    rf.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "size_bytes": rf.stat().st_size,
            }
        )

    # Read the latest report
    if report_files:
        latest = report_files[0]
        try:
            data = json.loads(latest.read_text())
            result["report"] = {
                "filename": latest.name,
                "content": data,
            }
        except (json.JSONDecodeError, OSError) as e:
            result["report"] = {"filename": latest.name, "error": str(e)}

    return result


def handle_generate_sprint_plan(args: dict[str, Any]) -> dict[str, Any]:
    """Trigger sprint plan generation by writing to the Build claw's sprint context."""
    from orchestrator.build.build_init import BuildFilesystemInit

    result: dict[str, Any] = {"status": "pending", "plan_path": ""}

    # Ensure build sandbox exists
    build_base = claw_base("build")
    if not build_base.exists():
        init_result = BuildFilesystemInit().initialize()
        result["sandbox_init"] = {
            "created_dirs": init_result.created_dirs,
            "failed": init_result.failed,
        }
        if init_result.failed:
            result["status"] = "error"
            result["error"] = f"Sandbox init failed: {init_result.failed}"
            return result

    # Write a sprint plan request file
    sprint_dir = build_base / "context" / "sprint"
    sprint_dir.mkdir(parents=True, exist_ok=True)

    plan_request = {
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": "assistant",
        "status": "pending",
        "instructions": args.get(
            "instructions", "Generate sprint plan from current backlog"
        ),
        "backlog_source": args.get("backlog_source", "github_issues"),
    }

    plan_file = sprint_dir / "sprint-plan-request.json"
    plan_file.write_text(json.dumps(plan_request, indent=2))
    result["plan_path"] = str(plan_file)
    return result


def handle_approve_sprint_plan(args: dict[str, Any]) -> dict[str, Any]:
    """Approve a pending sprint plan and update current-plan.json."""
    from orchestrator.build.build_init import BuildFilesystemInit
    from orchestrator.build.build_init import BuildOperationalLog
    from orchestrator.build.approval_handler import BuildApprovalHandler, PRActivityLog, DeployActivityLog
    from orchestrator.build.issue_manager import IssueManager

    plan_id = args.get("plan_id")
    if not plan_id:
        return {"status": "error", "error": "Missing plan_id"}

    build_base = claw_base("build")
    fs = BuildFilesystemInit(build_base)
    op_log = BuildOperationalLog(build_base / "logs/operational.log")
    pr_log = PRActivityLog(build_base / "logs/pr-activity.log")
    dep_log = DeployActivityLog(build_base / "logs/deploy-activity.log")

    approval = BuildApprovalHandler(fs, op_log, pr_log, dep_log)
    manager = IssueManager(fs, None, None, None, approval, op_log)

    result = manager.handle_sprint_plan_approved(plan_id)
    if result:
        return {"status": "approved", "first_issue": result}
    else:
        return {"status": "error", "error": f"Failed to approve plan {plan_id} (not found or already approved)"}


def handle_run_opportunity_scoring(args: dict[str, Any]) -> dict[str, Any]:
    """Trigger opportunity scoring by writing to the Analytics claw's context."""
    sandbox = claw_base("analytics")
    result: dict[str, Any] = {"status": "pending", "request_path": ""}

    if not sandbox.exists():
        result["note"] = "Analytics sandbox not initialized."
        return result

    context_dir = sandbox / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    scoring_request = {
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": "assistant",
        "status": "pending",
        "criteria": args.get(
            "criteria", ["revenue_potential", "client_fit", "effort_estimate"]
        ),
        "scope": args.get("scope", "all_opportunities"),
    }

    request_file = context_dir / "opportunity-scoring-request.json"
    request_file.write_text(json.dumps(scoring_request, indent=2))
    result["request_path"] = str(request_file)
    result["status"] = "request_written"

    return result


def handle_generate_weekly_report(args: dict[str, Any]) -> dict[str, Any]:
    """Generate a weekly report by aggregating data from all claws."""
    squad_id = args.get("squad_id", "default")
    week_start = args.get("week_start")

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week_start": week_start or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "claws": {},
    }

    # Aggregate from each claw
    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        claw_info: dict[str, Any] = {"role": role}

        # Tool count
        registry_file = tools_dir(squad_id, role) / "registry.json"
        if registry_file.exists():
            try:
                reg_data = json.loads(registry_file.read_text())
                claw_info["tool_count"] = len(reg_data.get("tools", {}))
                claw_info["last_evolution"] = reg_data.get("last_evolution")
            except (json.JSONDecodeError, OSError):
                claw_info["tool_count"] = 0
        else:
            claw_info["tool_count"] = 0

        # Health status
        health_file = health_dir(squad_id) / f"{role}.json"
        if health_file.exists():
            try:
                claw_info["health"] = json.loads(health_file.read_text())
            except (json.JSONDecodeError, OSError):
                claw_info["health"] = "unreadable"
        else:
            claw_info["health"] = "no_data"

        # Pending messages
        inbox = milimo_mesh_dir() / "inbox" / role
        if inbox.exists():
            claw_info["pending_messages"] = len(list(inbox.glob("*.json")))
        else:
            claw_info["pending_messages"] = 0

        report["claws"][role] = claw_info

    # Write report to analytics reports directory
    reports_dir = claw_base("analytics") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"weekly-report-{report['week_start']}.json"
    report_file.write_text(json.dumps(report, indent=2))
    report["report_path"] = str(report_file)

    return report


def handle_check_all_deadlines(args: dict[str, Any]) -> dict[str, Any]:
    """Check deadlines across all claws."""
    result: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "deadlines": [],
    }
    now = datetime.now(timezone.utc)

    # Check Build claw sprint deadlines
    sprint_plan = claw_base("build") / "context/sprint/current-plan.json"
    if sprint_plan.exists():
        try:
            data = json.loads(sprint_plan.read_text())
            if data.get("status") != "empty" and data.get("deadline"):
                deadline = datetime.fromisoformat(data["deadline"])
                result["deadlines"].append(
                    {
                        "claw": "build",
                        "type": "sprint",
                        "deadline": data["deadline"],
                        "days_remaining": (deadline - now).days,
                        "status": "upcoming" if deadline > now else "overdue",
                    }
                )
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # Check Content claw draft deadlines
    content_data = claw_base("content") / "data"
    if content_data.exists():
        for draft_file in content_data.glob("*.json"):
            try:
                data = json.loads(draft_file.read_text())
                if data.get("deadline"):
                    deadline = datetime.fromisoformat(data["deadline"])
                    result["deadlines"].append(
                        {
                            "claw": "content",
                            "type": "draft",
                            "draft_id": data.get("draft_id", draft_file.stem),
                            "deadline": data["deadline"],
                            "days_remaining": (deadline - now).days,
                            "status": "upcoming" if deadline > now else "overdue",
                        }
                    )
            except (json.JSONDecodeError, OSError, ValueError):
                pass

    # Check Ops claw project deadlines
    ops_data = claw_base("ops")
    if ops_data.exists():
        for project_file in ops_data.glob("*.json"):
            try:
                data = json.loads(project_file.read_text())
                if data.get("deadline"):
                    deadline = datetime.fromisoformat(data["deadline"])
                    result["deadlines"].append(
                        {
                            "claw": "ops",
                            "type": "project",
                            "project_id": data.get("project_id", project_file.stem),
                            "deadline": data["deadline"],
                            "days_remaining": (deadline - now).days,
                            "status": "upcoming" if deadline > now else "overdue",
                        }
                    )
            except (json.JSONDecodeError, OSError, ValueError):
                pass

    # Sort by urgency
    result["deadlines"].sort(key=lambda d: d.get("days_remaining", 999))
    result["total_deadlines"] = len(result["deadlines"])
    result["overdue_count"] = sum(
        1 for d in result["deadlines"] if d["status"] == "overdue"
    )

    return result


def handle_run_dependency_audit(args: dict[str, Any]) -> dict[str, Any]:
    """Run a dependency audit on the Build claw's repo."""
    import subprocess

    result: dict[str, Any] = {"status": "pending", "audit_path": ""}

    repo_path = claw_base("build") / "repo"
    if not repo_path.exists():
        result["note"] = "Build repo not found. Clone a repo first."
        return result

    audits: list[dict[str, Any]] = []

    # Python dependencies
    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        try:
            pip_audit = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(repo_path),
            )
            if pip_audit.returncode == 0:
                outdated = json.loads(pip_audit.stdout)
                audits.append(
                    {
                        "type": "python",
                        "outdated_count": len(outdated),
                        "packages": outdated[:20],  # Limit output
                    }
                )
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            audits.append({"type": "python", "error": "audit_failed"})

    # Node.js dependencies
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            npm_audit = subprocess.run(
                ["npm", "audit", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(repo_path),
            )
            if npm_audit.returncode != 0 or npm_audit.stdout:
                try:
                    audit_data = json.loads(npm_audit.stdout)
                    audits.append(
                        {
                            "type": "nodejs",
                            "vulnerabilities": audit_data.get("vulnerabilities", {}),
                            "metadata": audit_data.get("metadata", {}),
                        }
                    )
                except json.JSONDecodeError:
                    audits.append(
                        {"type": "nodejs", "raw_output": npm_audit.stdout[:500]}
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            audits.append({"type": "nodejs", "error": "audit_failed"})

    result["audits"] = audits
    result["status"] = "complete"
    result["audited_at"] = datetime.now(timezone.utc).isoformat()

    # Write audit result
    audit_dir = claw_base("build") / "context/audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = (
        audit_dir
        / f"dependency-audit-{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    )
    audit_file.write_text(json.dumps(result, indent=2))
    result["audit_path"] = str(audit_file)

    return result


def handle_discover_tools(args: dict[str, Any]) -> dict[str, Any]:
    """Discover what tools each claw currently has deployed."""
    squad_id = args.get("squad_id", "default")
    result: dict[str, Any] = {
        "claws": {},
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }

    for role in ["content", "ops", "analytics", "finance", "build", "assistant"]:
        claw_tools: dict[str, Any] = {"tools": [], "count": 0, "last_evolution": None}

        registry_file = tools_dir(squad_id, role) / "registry.json"
        if registry_file.exists():
            try:
                reg_data = json.loads(registry_file.read_text())
                tools = reg_data.get("tools", {})
                claw_tools["tools"] = [
                    {"name": name, "version": info.get("version", "unknown")}
                    for name, info in tools.items()
                ]
                claw_tools["count"] = len(tools)
                claw_tools["last_evolution"] = reg_data.get("last_evolution")
            except (json.JSONDecodeError, OSError):
                pass

        result["claws"][role] = claw_tools

    result["total_tools"] = sum(c["count"] for c in result["claws"].values())
    return result


def handle_get_result(args: dict[str, Any]) -> dict[str, Any]:
    """Get the result of a previously sent message from the outbox.

    After sending a message via send_to_claw, use this to poll for the result.
    Results are stored in OUTBOX_DIR/{role}/{message_id}.json and expire after 1 hour.

    Args:
        message_id: The message_id returned by send_to_claw
        role: The claw role that processed the message (optional, will search all if not provided)

    Returns:
        The result data if found, or status indicating pending/not found
    """
    message_id = args.get("message_id", "")
    role = args.get("role", "")

    if not message_id:
        raise RuntimeError("message_id is required")

    _mesh_dir = milimo_mesh_dir()
    outbox_dir = _mesh_dir / "outbox"

    if not outbox_dir.exists():
        return {"status": "not_found", "message": "No outbox directory exists"}

    roles_to_check = (
        [role]
        if role
        else ["content", "ops", "analytics", "finance", "build", "assistant"]
    )

    for check_role in roles_to_check:
        result_file = outbox_dir / check_role / f"{message_id}.json"
        if result_file.exists():
            try:
                data = json.loads(result_file.read_text())
                expires_at = data.get("expires_at")
                if expires_at:
                    try:
                        expiry_dt = datetime.fromisoformat(
                            expires_at.replace("Z", "+00:00")
                        )
                        if datetime.now(timezone.utc) > expiry_dt:
                            return {
                                "status": "expired",
                                "message": "Result has expired",
                            }
                    except ValueError:
                        pass

                return {
                    "status": "found",
                    "role": check_role,
                    "message_id": message_id,
                    "original_message": data.get("original_message"),
                    "result": data.get("result"),
                    "processed_at": data.get("processed_at"),
                    "expires_at": expires_at,
                }
            except (json.JSONDecodeError, OSError) as e:
                return {"status": "error", "message": f"Failed to read result: {e}"}

    return {
        "status": "pending",
        "message": f"No result found for message_id {message_id}",
    }


# ---------------------------------------------------------------------------
# Claw Lifecycle Commands (Phase 4)
# ---------------------------------------------------------------------------


def handle_start_claw(args: dict[str, Any]) -> dict[str, Any]:
    """Start a specific claw role via the launcher.

    Args:
        role: The claw role to start (content, ops, analytics, finance, build, assistant)

    Returns:
        Dict with started status and role info
    """
    import subprocess
    import os

    role = args.get("role", "")
    if not role:
        raise RuntimeError("role is required")

    valid_roles = ["content", "ops", "analytics", "finance", "build", "assistant"]
    if role not in valid_roles:
        raise RuntimeError(
            f"Invalid role '{role}'. Must be one of: {', '.join(valid_roles)}"
        )

    _mesh_dir = milimo_mesh_dir()
    launcher_pid_file = _mesh_dir / "launcher.pid"
    blueprint_path = blueprints_dir("0.1.0")

    if not launcher_pid_file.exists():
        raise RuntimeError("Launcher not running. Start the launcher first.")

    launcher_pid = int(launcher_pid_file.read_text().strip())

    try:
        os.kill(launcher_pid, 0)
    except ProcessLookupError:
        raise RuntimeError(f"Launcher (PID {launcher_pid}) is not running")

    hb_file = _mesh_dir / "heartbeats" / f"{role}.json"
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text())
            timestamp = hb.get("timestamp", "")
            if timestamp:
                hb_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - hb_time).total_seconds()
                if age < 90:
                    return {
                        "status": "already_running",
                        "role": role,
                        "message": f"{role} claw is already running (heartbeat {age:.0f}s old)",
                    }
        except Exception:
            pass

    subprocess.run(
        [
            "python3",
            str(blueprint_path / "orchestrator" / "claw_launcher.py"),
            "--role",
            role,
        ],
        check=False,
        capture_output=True,
    )

    import time

    for _ in range(10):
        time.sleep(1)
        if hb_file.exists():
            return {
                "status": "started",
                "role": role,
                "message": f"{role} claw started successfully",
            }

    return {
        "status": "pending",
        "role": role,
        "message": f"{role} claw start initiated, waiting for heartbeat",
    }


def handle_stop_claw(args: dict[str, Any]) -> dict[str, Any]:
    """Stop a specific claw role.

    Args:
        role: The claw role to stop

    Returns:
        Dict with stopped status
    """
    role = args.get("role", "")
    if not role:
        raise RuntimeError("role is required")

    _mesh_dir = milimo_mesh_dir()
    hb_file = _mesh_dir / "heartbeats" / f"{role}.json"

    if not hb_file.exists():
        return {
            "status": "not_running",
            "role": role,
            "message": f"{role} claw is not running",
        }

    hb = json.loads(hb_file.read_text())
    pid = hb.get("pid")

    if pid:
        try:
            import os
            import signal

            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.warning("Failed to kill %s process: %s", role, e)

    hb_file.unlink(missing_ok=True)

    return {
        "status": "stopped",
        "role": role,
        "message": f"{role} claw stopped",
        "previous_pid": pid,
    }


def handle_restart_claw(args: dict[str, Any]) -> dict[str, Any]:
    """Restart a specific claw role.

    Args:
        role: The claw role to restart

    Returns:
        Dict with restart status
    """
    import time

    role = args.get("role", "")
    if not role:
        raise RuntimeError("role is required")

    handle_stop_claw({"role": role})

    time.sleep(2)

    return handle_start_claw({"role": role})


def handle_restart_all_claws(args: dict[str, Any]) -> dict[str, Any]:
    """Restart all claws.

    Returns:
        Dict with restart status for each claw
    """
    import time

    roles = ["content", "ops", "analytics", "finance", "build", "assistant"]
    results = {}

    for role in roles:
        handle_stop_claw({"role": role})

    time.sleep(2)

    for role in roles:
        results[role] = handle_start_claw({"role": role})

    return {
        "status": "completed",
        "results": results,
        "message": "All claws restarted",
    }


def handle_start_launcher(args: dict[str, Any]) -> dict[str, Any]:
    """Start the claw launcher as a background daemon.

    Returns:
        Dict with launcher PID and startup status
    """
    import os
    import subprocess
    import time

    _mesh_dir = milimo_mesh_dir()
    launcher_pid_file = _mesh_dir / "launcher.pid"

    if launcher_pid_file.exists():
        try:
            pid = int(launcher_pid_file.read_text().strip())
            os.kill(pid, 0)
            return {
                "status": "already_running",
                "launcher_pid": pid,
                "message": f"Launcher already running (PID {pid})",
            }
        except ProcessLookupError:
            launcher_pid_file.unlink(missing_ok=True)

    blueprint_path = blueprints_dir("0.1.0")
    launcher_script = blueprint_path / "orchestrator" / "claw_launcher.py"

    if not launcher_script.exists():
        raise RuntimeError(f"Launcher script not found: {launcher_script}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(blueprint_path)

    subprocess.Popen(
        [
            "python3",
            str(launcher_script),
            "--all",
            "--daemon",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(15):
        time.sleep(1)
        if launcher_pid_file.exists():
            try:
                pid = int(launcher_pid_file.read_text().strip())
                os.kill(pid, 0)
                return {
                    "status": "started",
                    "launcher_pid": pid,
                    "message": f"Launcher started successfully (PID {pid})",
                }
            except (ValueError, ProcessLookupError):
                pass

    return {
        "status": "pending",
        "launcher_pid": None,
        "message": "Launcher start initiated, waiting for PID file",
    }


def handle_claw_logs(args: dict[str, Any]) -> dict[str, Any]:
    """Get recent log lines for a specific claw.

    Args:
        role: The claw role
        lines: Number of lines to return (default 50)

    Returns:
        Dict with log lines
    """
    role = args.get("role", "")
    if not role:
        raise RuntimeError("role is required")

    lines = args.get("lines", 50)

    _mesh_dir = milimo_mesh_dir()
    log_file = _mesh_dir / "logs" / "launcher.log"

    if not log_file.exists():
        return {
            "role": role,
            "lines": [],
            "message": "No log file found",
        }

    try:
        all_lines = log_file.read_text().splitlines()
        role_lines = [
            line for line in all_lines if f".{role}]" in line or f" {role} " in line
        ]
        recent_lines = role_lines[-lines:] if len(role_lines) > lines else role_lines

        return {
            "role": role,
            "lines": recent_lines,
            "total_lines": len(role_lines),
            "returned": len(recent_lines),
        }
    except Exception as e:
        raise RuntimeError(f"Failed to read logs: {e}")


def handle_launcher_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get the current launcher status.

    Returns:
        Dict with launcher status, PID, and claw statuses
    """
    import os

    _mesh_dir = milimo_mesh_dir()
    launcher_pid_file = _mesh_dir / "launcher.pid"

    status = {
        "launcher_running": False,
        "launcher_pid": None,
        "claws": {},
    }

    pid = None
    if launcher_pid_file.exists():
        try:
            pid = int(launcher_pid_file.read_text().strip())
            os.kill(pid, 0)
            status["launcher_running"] = True
            status["launcher_pid"] = pid
        except ProcessLookupError:
            status["launcher_running"] = False
            status["launcher_pid"] = pid
        except Exception:
            pass

    roles = ["content", "ops", "analytics", "finance", "build", "assistant"]
    for role in roles:
        hb_file = _mesh_dir / "heartbeats" / f"{role}.json"
        if hb_file.exists():
            try:
                hb = json.loads(hb_file.read_text())
                timestamp = hb.get("timestamp", "")
                if not timestamp:
                    status["claws"][role] = {
                        "status": "unknown",
                        "diagnostic_note": "Heartbeat file has no timestamp — may be corrupt",
                    }
                else:
                    hb_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - hb_time).total_seconds()
                    claw_status = "running" if age < 90 else "stale"
                    status["claws"][role] = {
                        "status": claw_status,
                        "pid": hb.get("pid"),
                        "uptime_seconds": hb.get("uptime_seconds"),
                        "heartbeat_age_seconds": round(age, 1),
                    }
                    if claw_status == "stale":
                        status["claws"][role]["diagnostic_note"] = (
                            f"Heartbeat is {round(age)}s old — claw may be unresponsive"
                        )
            except Exception:
                status["claws"][role] = {
                    "status": "unknown",
                    "diagnostic_note": "Failed to parse heartbeat file",
                }
        else:
            status["claws"][role] = {
                "status": "stopped",
                "diagnostic_note": "No heartbeat file — claw was never started or has been stopped",
            }

    return status


def handle_milimo_status(args: dict[str, Any]) -> dict[str, Any]:
    """Aggregate overview: launcher + health + evolution + pending for all claws."""
    squad_id = args.get("squad_id", "default")
    roles = ["content", "ops", "analytics", "finance", "build", "assistant"]

    launcher = handle_launcher_status({})
    health_file = health_dir(squad_id) / "health.json"
    health_data: dict[str, Any] = {}
    if health_file.exists():
        try:
            health_data = json.loads(health_file.read_text()).get("claws", {})
        except (json.JSONDecodeError, OSError):
            pass
    evolution_summary = _read_evolution_summary()
    by_role = evolution_summary.get("by_role", {})

    claws: dict[str, Any] = {}
    for role in roles:
        launcher_claw = launcher.get("claws", {}).get(role, {})
        claw_health = health_data.get(role, {})
        evo_role = by_role.get(role, {})
        last_stage = evo_role.get("last_stage")
        if last_stage == "deploy":
            evo_status = "success"
        elif last_stage == "error":
            evo_status = "error"
        elif last_stage is not None:
            evo_status = "incomplete"
        elif role in by_role:
            evo_status = "unknown"
        else:
            evo_status = "never_run"

        pending_count = 0
        inbox = milimo_mesh_dir() / "inbox" / role
        if inbox.exists():
            pending_count = sum(1 for _ in inbox.glob("*.json"))

        claws[role] = {
            "launcher_status": launcher_claw.get("status", "unknown"),
            "health_score": claw_health.get("score"),
            "evolution_status": evo_status,
            "tools_deployed": evo_role.get("tools_deployed", 0),
            "pending_messages": pending_count,
        }

    return {
        "launcher_running": launcher.get("launcher_running", False),
        "launcher_pid": launcher.get("launcher_pid"),
        "claws": claws,
        "evolution_ever_run": bool(by_role),
        "diagnostic_note": (
            "Evolution cycle has never run — 0 tools is expected"
            if not by_role
            else None
        ),
    }


COMMAND_HANDLERS: dict[str, Any] = {
    "evolution_status": handle_evolution_status,
    "blueprint_info": handle_blueprint_info,
    "blueprint_list": handle_blueprint_list,
    "blueprint_diff": handle_blueprint_diff,
    "blueprint_export": handle_blueprint_export,
    "blueprint_rollback": handle_blueprint_rollback,
    "tool_registry": handle_tool_registry,
    "marketplace_search": handle_marketplace_search,
    "marketplace_download": handle_marketplace_download,
    "marketplace_publish": handle_marketplace_publish,
    "mesh_flow_state": handle_mesh_flow_state,
    "health_status": handle_health_status,
    "provenance_verify": handle_provenance_verify,
    "provenance_keygen": handle_provenance_keygen,
    "revenue_summary": handle_revenue_summary,
    "morning_brief": handle_morning_brief,
    "evening_wrap": handle_evening_wrap,
    "activate_deep_work": handle_activate_deep_work,
    "resume_deep_work": handle_resume_deep_work,
    "deep_work_status": handle_deep_work_status,
    "collect_health": handle_collect_health,
    "squad_config": handle_squad_config,
    "send_to_claw": handle_send_to_claw,
    "claw_status": handle_claw_status,
    "ops_active_projects": handle_ops_active_projects,
    "content_pending_drafts": handle_content_pending_drafts,
    "build_open_prs": handle_build_open_prs,
    "analytics_latest_report_summary": handle_analytics_latest_report_summary,
    "generate_sprint_plan": handle_generate_sprint_plan,
    "approve_sprint_plan": handle_approve_sprint_plan,
    "run_opportunity_scoring": handle_run_opportunity_scoring,
    "generate_weekly_report": handle_generate_weekly_report,
    "check_all_deadlines": handle_check_all_deadlines,
    "run_dependency_audit": handle_run_dependency_audit,
    "discover_tools": handle_discover_tools,
    "get_result": handle_get_result,
    "start_claw": handle_start_claw,
    "stop_claw": handle_stop_claw,
    "restart_claw": handle_restart_claw,
    "restart_all_claws": handle_restart_all_claws,
    "start_launcher": handle_start_launcher,
    "claw_logs": handle_claw_logs,
    "launcher_status": handle_launcher_status,
    "milimo_status": handle_milimo_status,
}


def handle_command(command: str, args: dict[str, Any], blueprint_dir: str = "") -> dict[str, Any]:
    """Helper to dispatch commands programmatically (used by RPC server)."""
    if command not in COMMAND_HANDLERS:
        raise ValueError(f"Unknown command: {command}")
    handler = COMMAND_HANDLERS[command]
    return handler(args)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Milimo Claw Bridge CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--command",
        required=True,
        help="Command to execute",
        choices=list(COMMAND_HANDLERS.keys()),
    )
    parser.add_argument(
        "--args",
        required=False,
        default="{}",
        help="JSON-encoded arguments for the command",
    )

    args = parser.parse_args()

    # Parse arguments
    try:
        command_args = json.loads(args.args)
        if not isinstance(command_args, dict):
            command_args = {}
    except json.JSONDecodeError as e:
        response = {"success": False, "error": f"Invalid JSON arguments: {e}"}
        print(json.dumps(response))
        sys.exit(1)

    # Execute command
    command = args.command
    if command not in COMMAND_HANDLERS:
        response = {"success": False, "error": f"Unknown command: {command}"}
        print(json.dumps(response))
        sys.exit(1)

    try:
        handler = COMMAND_HANDLERS[command]
        result = handler(command_args)
        response = {"success": True, "data": result}
    except RuntimeError as e:
        response = {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("Unexpected error executing command")
        response = {"success": False, "error": f"Unexpected error: {e}"}

    # Output only JSON to stdout
    print(json.dumps(response))


if __name__ == "__main__":
    main()
