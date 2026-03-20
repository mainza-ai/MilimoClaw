#!/usr/bin/env python3
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


def handle_evolution_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get evolution status for a specific claw."""
    from .evolution_cycle import EvolutionCycle
    from .tool_registry import ToolRegistry

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw", "content")
    blueprint_dir = args.get("blueprint_dir", ".")

    try:
        registry = ToolRegistry(squad_id, claw_role)
        cycle = EvolutionCycle(
            squad_id=squad_id,
            claw_role=claw_role,
            blueprint_dir=blueprint_dir,
        )
        tools = registry.get_inventory()
        return {
            "status": "idle",
            "last_cycle": None,
            "tools_deployed": len(tools),
            "pending_proposals": 0,
        }
    except Exception as e:
        logger.exception("Failed to get evolution status")
        raise RuntimeError(f"Evolution status error: {e}") from e


def handle_blueprint_info(args: dict[str, Any]) -> dict[str, Any]:
    """Get blueprint information."""
    from .blueprint_manager import BlueprintManager

    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")
    blueprint_dir = args.get("blueprint_dir", ".")

    try:
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
    from .blueprint_manager import BlueprintManager

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
    from .blueprint_manager import BlueprintManager

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
    from .blueprint_manager import BlueprintManager

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
    from .blueprint_manager import BlueprintManager

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
    from .tool_registry import ToolRegistry

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
    from .marketplace_manager import MarketplaceManager

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
    from .marketplace_manager import MarketplaceManager

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
    from .blueprint_manager import BlueprintManager
    from .marketplace_manager import MarketplaceManager

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
    """Get cross-claw mesh signal flow state."""
    squad_id = args.get("squad", "default")

    try:
        return {
            "signals": [],
            "last_transmission": None,
            "signal_count_this_week": 0,
        }
    except Exception as e:
        logger.exception("Failed to get mesh flow state")
        raise RuntimeError(f"Mesh flow state error: {e}") from e


def handle_health_status(args: dict[str, Any]) -> dict[str, Any]:
    """Get health status for claws."""
    squad_id = args.get("squad_id", "default")

    try:
        from pathlib import Path
        import json
        home = Path.home()
        health_dir = home / ".milimo" / "health" / squad_id
        if not health_dir.exists():
            return {}
        status = {}
        for f in health_dir.glob("*.json"):
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
    from .provenance_verifier import ProvenanceVerifier
    from .provenance_signer import Attestation

    blueprint_dir = args.get("blueprint_dir", ".")
    version = args.get("version", "latest")
    strict = args.get("strict", False)
    squad_id = args.get("squad_id", "default")
    claw_role = args.get("claw_role", "content")

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
    from .provenance_signer import generate_key_pair, save_key_pair

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


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------

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
}


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
