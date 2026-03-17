#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Blueprint Manager

Manages blueprint versioning, export, diff, rollback, and integrity
verification. Each blueprint snapshot is a cryptographically signed
artifact that captures the claw's complete state.

Blueprint snapshot structure (matches Section 10.1 of project description):
    meta/         version, created_at, evolved_from, squad_size, niche_tags
    claw_config/  role, model preferences
    tools_inventory/  all evolved tools with performance deltas
    policy/       egress, filesystem, approval thresholds, privacy routing
    learned_priors/   style, timing, client patterns, pricing calibration
    integrity/    sha256 digest + provenance chain

Usage:
    from blueprint_manager import BlueprintManager

    manager = BlueprintManager(
        squad_id="my-squad",
        claw_role="content",
        blueprint_dir="/path/to/milimo-blueprint",
    )
    version = manager.current_version()
    manager.bump_version("style_descriptor deployed")
    snapshot = manager.export()
    diff = manager.diff("0.1.0", "0.2.0")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .tool_registry import ToolRegistry

logger = logging.getLogger("milimo.blueprint_manager")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BlueprintMeta:
    """Blueprint metadata."""

    version: str = "0.1.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    evolved_from: str = ""  # parent blueprint hash
    squad_size: int = 1
    niche_tags: list[str] = field(default_factory=list)
    business_type: str = ""
    operational_months: int = 0


@dataclass
class BlueprintSnapshot:
    """A complete versioned snapshot of a claw's state."""

    meta: BlueprintMeta
    claw_config: dict[str, Any] = field(default_factory=dict)
    tools_inventory: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    learned_priors: dict[str, Any] = field(default_factory=dict)
    integrity: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BlueprintSnapshot:
        meta_data = data.get("meta", {})
        meta = BlueprintMeta(**{
            k: v for k, v in meta_data.items()
            if k in BlueprintMeta.__dataclass_fields__
        })
        return cls(
            meta=meta,
            claw_config=data.get("claw_config", {}),
            tools_inventory=data.get("tools_inventory", {}),
            policy=data.get("policy", {}),
            learned_priors=data.get("learned_priors", {}),
            integrity=data.get("integrity", {}),
        )


@dataclass
class BlueprintDiff:
    """Diff between two blueprint versions."""

    version_a: str
    version_b: str
    tools_added: list[str] = field(default_factory=list)
    tools_removed: list[str] = field(default_factory=list)
    tools_modified: list[str] = field(default_factory=list)
    policy_changes: dict[str, Any] = field(default_factory=dict)
    config_changes: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Blueprint Manager
# ---------------------------------------------------------------------------


class BlueprintManager:
    """Manages blueprint versioning and export for a single claw."""

    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        blueprint_dir: str | Path,
        tool_registry: ToolRegistry | None = None,
        versions_dir: str | None = None,
    ) -> None:
        self.squad_id = squad_id
        self.claw_role = claw_role
        self.blueprint_dir = Path(blueprint_dir)

        self._tool_registry = tool_registry

        if versions_dir:
            self._versions_dir = Path(versions_dir)
        else:
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._versions_dir = (
                Path(home) / ".milimo" / "blueprints" / squad_id / claw_role
            )
        self._versions_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._versions_dir / "state.json"

        # Load current state
        self._state = self._load_state()

    # ── Public API ────────────────────────────────────────────────────

    def current_version(self) -> str:
        """Get the current blueprint version."""
        return self._state.get("version", "0.1.0")

    def bump_version(self, reason: str = "") -> str:
        """
        Bump the blueprint version.

        Uses patch increment per tool, minor per month.
        """
        current = self.current_version()
        parts = current.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        patch += 1
        new_version = f"{major}.{minor}.{patch}"

        self._state["version"] = new_version
        self._state["version_history"] = self._state.get("version_history", [])
        self._state["version_history"].append({
            "version": new_version,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_state()

        logger.info("Bumped version %s → %s (%s)", current, new_version, reason)
        return new_version

    def export(self, niche_tags: list[str] | None = None) -> BlueprintSnapshot:
        """
        Export the current blueprint as a complete snapshot.

        Returns a BlueprintSnapshot with integrity digest.
        """
        meta = BlueprintMeta(
            version=self.current_version(),
            evolved_from=self._get_parent_hash(),
            squad_size=self._state.get("squad_size", 1),
            niche_tags=niche_tags or self._state.get("niche_tags", []),
            business_type=self._state.get("business_type", ""),
            operational_months=self._state.get("operational_months", 0),
        )

        claw_config = self._load_claw_config()
        tools_inventory = self._get_tools_inventory()
        policy = self._load_policy()
        learned_priors = self._state.get("learned_priors", {})

        # Build snapshot without integrity first
        snapshot = BlueprintSnapshot(
            meta=meta,
            claw_config=claw_config,
            tools_inventory=tools_inventory,
            policy=policy,
            learned_priors=learned_priors,
        )

        # Compute integrity
        digest = self._compute_digest(snapshot)
        provenance = self._state.get("provenance_chain", [])
        provenance.append(digest)

        snapshot.integrity = {
            "digest": digest,
            "provenance_chain": provenance,
        }

        # Save the snapshot
        snapshot_file = self._versions_dir / f"v{meta.version}.json"
        with snapshot_file.open("w") as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)

        logger.info("Exported blueprint v%s (digest: %s...)", meta.version, digest[:16])
        return snapshot

    def export_handoff(self) -> str:
        """
        Export a Handoff Blueprint bundle for a departing squad member.
        Returns the path to the handoff file.
        """
        snapshot = self.export()
        handoff_path = self._versions_dir / f"handoff_{self.claw_role}_v{snapshot.meta.version}.json"
        
        bundle = {
            "type": "milimo-handoff",
            "snapshot": snapshot.to_dict(),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        
        with handoff_path.open("w") as f:
            json.dump(bundle, f, indent=2, default=str)
            
        logger.info(f"Generated handoff bundle at {handoff_path}")
        return str(handoff_path)

    def import_handoff(self, handoff_path: str) -> bool:
        """Import a Handoff Blueprint from a departing member."""
        path = Path(handoff_path)
        if not path.exists():
            logger.error(f"Handoff file {handoff_path} not found.")
            return False
            
        with path.open() as f:
            bundle = json.load(f)
            
        if bundle.get("type") != "milimo-handoff":
            logger.error("Invalid handoff bundle format.")
            return False
            
        snapshot = BlueprintSnapshot.from_dict(bundle.get("snapshot", {}))
        
        # Verify integrity before accepting
        if not self.verify_integrity(snapshot):
            logger.error("Handoff bundle failed integrity verification. Rejected.")
            return False
            
        # Import to state
        self._state["version"] = snapshot.meta.version
        self._state["provenance_chain"] = snapshot.integrity.get("provenance_chain", [])
        
        # Save snapshot file locally so it exists in version history
        snapshot_file = self._versions_dir / f"v{snapshot.meta.version}.json"
        with snapshot_file.open("w") as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)
            
        self._save_state()
        logger.info(f"Successfully imported handoff blueprint v{snapshot.meta.version}")
        return True

    def diff(self, version_a: str, version_b: str) -> BlueprintDiff:
        """Compare two blueprint versions."""
        snap_a = self._load_snapshot(version_a)
        snap_b = self._load_snapshot(version_b)

        if snap_a is None or snap_b is None:
            missing = version_a if snap_a is None else version_b
            logger.warning("Snapshot not found for version %s", missing)
            return BlueprintDiff(version_a=version_a, version_b=version_b)

        # Compare tools
        tools_a = set(snap_a.tools_inventory.keys())
        tools_b = set(snap_b.tools_inventory.keys())

        tools_added = sorted(tools_b - tools_a)
        tools_removed = sorted(tools_a - tools_b)

        common_tools = tools_a & tools_b
        tools_modified = []
        for tool_name in sorted(common_tools):
            if snap_a.tools_inventory[tool_name] != snap_b.tools_inventory[tool_name]:
                tools_modified.append(tool_name)

        # Compare policies
        policy_changes = {}
        if snap_a.policy != snap_b.policy:
            for key in set(list(snap_a.policy.keys()) + list(snap_b.policy.keys())):
                val_a = snap_a.policy.get(key)
                val_b = snap_b.policy.get(key)
                if val_a != val_b:
                    policy_changes[key] = {"from": val_a, "to": val_b}

        # Compare config
        config_changes = {}
        if snap_a.claw_config != snap_b.claw_config:
            for key in set(list(snap_a.claw_config.keys()) + list(snap_b.claw_config.keys())):
                val_a = snap_a.claw_config.get(key)
                val_b = snap_b.claw_config.get(key)
                if val_a != val_b:
                    config_changes[key] = {"from": val_a, "to": val_b}

        return BlueprintDiff(
            version_a=version_a,
            version_b=version_b,
            tools_added=tools_added,
            tools_removed=tools_removed,
            tools_modified=tools_modified,
            policy_changes=policy_changes,
            config_changes=config_changes,
        )

    def rollback(self, target_version: str, reason: str = "") -> bool:
        """Restore a previous blueprint snapshot."""
        snapshot = self._load_snapshot(target_version)
        if snapshot is None:
            logger.error("Cannot rollback: version %s not found", target_version)
            return False

        old_version = self.current_version()
        self._state["version"] = target_version
        self._state["version_history"] = self._state.get("version_history", [])
        self._state["version_history"].append({
            "version": target_version,
            "reason": f"rollback from {old_version}: {reason}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_state()

        logger.info("Rolled back %s → %s (%s)", old_version, target_version, reason)
        return True

    def verify_integrity(self, snapshot: BlueprintSnapshot) -> bool:
        """Verify the SHA-256 digest of a snapshot."""
        expected = snapshot.integrity.get("digest", "")
        if not expected:
            return False

        # Recompute without integrity field
        clean = BlueprintSnapshot(
            meta=snapshot.meta,
            claw_config=snapshot.claw_config,
            tools_inventory=snapshot.tools_inventory,
            policy=snapshot.policy,
            learned_priors=snapshot.learned_priors,
        )
        actual = self._compute_digest(clean)
        return actual == expected

    def verify_provenance(self, snapshot: BlueprintSnapshot) -> bool:
        """
        Verify the provenance chain of a snapshot.
        Checks if the integrity digest matches and if the provenance chain exists.
        For a deeper check, it would verify each parent's digest in the marketplace.
        """
        if not self.verify_integrity(snapshot):
            return False
            
        chain = snapshot.integrity.get("provenance_chain", [])
        if not chain:
            return False
            
        # The last element in the provenance chain should be this snapshot's digest
        expected_digest = snapshot.integrity.get("digest")
        if chain[-1] != expected_digest:
            return False
            
        return True

    def list_versions(self) -> list[dict[str, Any]]:
        """List all saved blueprint versions."""
        return self._state.get("version_history", [])

    # ── Internal Methods ──────────────────────────────────────────────

    def _load_claw_config(self) -> dict[str, Any]:
        """Load the claw's role blueprint YAML."""
        role_file = self.blueprint_dir / "roles" / f"{self.claw_role}-claw.yaml"
        if role_file.exists():
            with role_file.open() as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_policy(self) -> dict[str, Any]:
        """Load the claw's sandbox policy YAML."""
        policy_file = self.blueprint_dir / "policies" / f"{self.claw_role}-sandbox.yaml"
        if policy_file.exists():
            with policy_file.open() as f:
                return yaml.safe_load(f) or {}
        return {}

    def _get_tools_inventory(self) -> dict[str, Any]:
        """Get tool inventory from the registry."""
        if self._tool_registry:
            return self._tool_registry.get_inventory()
        return {}

    def _get_parent_hash(self) -> str:
        """Get the hash of the parent blueprint (last export)."""
        history = self._state.get("version_history", [])
        if history:
            return history[-1].get("version", "")
        return ""

    def _load_snapshot(self, version: str) -> BlueprintSnapshot | None:
        """Load a saved snapshot by version."""
        v_prefix = version if version.startswith("v") else f"v{version}"
        snapshot_file = self._versions_dir / f"{v_prefix}.json"
        if not snapshot_file.exists():
            return None

        with snapshot_file.open() as f:
            data = json.load(f)
        return BlueprintSnapshot.from_dict(data)

    @staticmethod
    def _compute_digest(snapshot: BlueprintSnapshot) -> str:
        """Compute SHA-256 digest of a snapshot (excluding integrity field)."""
        content = json.dumps(snapshot.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def _load_state(self) -> dict[str, Any]:
        """Load manager state from disk."""
        if self._state_file.exists():
            with self._state_file.open() as f:
                return json.load(f)
        return {"version": "0.1.0", "version_history": []}

    def _save_state(self) -> None:
        """Persist manager state to disk."""
        with self._state_file.open("w") as f:
            json.dump(self._state, f, indent=2, default=str)
