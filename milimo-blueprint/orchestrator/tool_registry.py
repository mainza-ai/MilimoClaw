# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Registry

Manages the inventory of all evolved tools for a claw. Each claw
has its own registry at ~/.milimo/tools/<squadId>/<role>/registry.json.

Supports tool provenance signing with Ed25519 signatures and
automatic rollback on regression detection.

Usage:
from tool_registry import ToolRegistry
from tool_builder import BuiltTool

registry = ToolRegistry(squad_id="my-squad", claw_role="content")
registry.register(tool)
registry.disable("style_descriptor")
inventory = registry.get_inventory()
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .milimo_paths import tools_dir
from .tool_builder import BuiltTool

logger = logging.getLogger("milimo.tool_registry")

# Import provenance signing
try:
    from .provenance_signer import (
        generate_key_pair,
        load_key_pair,
        save_key_pair,
    )
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization  # noqa: F401
    from cryptography.exceptions import InvalidSignature

    PROVENANCE_AVAILABLE = True
except ImportError:
    PROVENANCE_AVAILABLE = False
    generate_key_pair = None
    load_key_pair = None
    save_key_pair = None


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ToolProvenance:
    """Provenance information for a deployed tool."""

    tool_id: str
    claw_role: str
    generated_at: str
    generation_model: str = "local-nim"
    trigger_pattern: str = ""
    backtest_result: dict[str, Any] = field(default_factory=dict)
    deployed_at: str = ""
    signature: str = ""
    signer_key_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolProvenance":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RollbackDecision:
    """Decision result for rollback check."""

    should_rollback: bool
    tool_name: str
    reason: str
    current_metric: float
    baseline_metric: float
    threshold: float
    days_since_deploy: int


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """
    Manages the inventory of evolved tools for a single claw.

    Supports registration, enable/disable, listing, persistence,
    provenance signing, and automatic rollback on regression.
    """

    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        registry_dir: str | None = None,
        max_tools: int = 30,
    ) -> None:
        self.squad_id = squad_id
        self.claw_role = claw_role
        self.max_tools = max_tools

        if registry_dir:
            self._dir = Path(registry_dir)
        else:
            self._dir = tools_dir(squad_id, claw_role)

        self._memory_only = False
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._memory_only = True
            logger.warning(
                "Cannot create tool registry directory %s (%s) — operating in memory-only mode",
                self._dir,
                e,
            )

        self._registry_file = self._dir / "registry.json"
        self._tools: dict[str, BuiltTool] = {}
        self._provenances: dict[str, ToolProvenance] = {}
        self._rollback_monitoring: dict[str, dict[str, Any]] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────

    def register(self, tool: BuiltTool) -> bool:
        """
        Register a newly deployed tool.

        Returns False if the registry is at capacity.
        """
        active_count = sum(1 for t in self._tools.values() if t.status != "disabled")
        if active_count >= self.max_tools:
            logger.warning(
                "Registry at capacity (%d/%d) for %s — cannot register '%s'",
                active_count,
                self.max_tools,
                self.claw_role,
                tool.tool_name,
            )
            return False

        tool.status = "deployed"
        self._tools[tool.tool_name] = tool

        # Sign and store provenance
        provenance = self._create_provenance(tool)
        if provenance:
            self._provenances[tool.tool_name] = provenance
            self._rollback_monitoring[tool.tool_name] = {
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "baseline_metric": tool.baseline_score,
                "threshold": 0.95,  # 95% of baseline
                "checks": [],
            }

        self._save()

        logger.info(
            "Registered tool '%s' for %s (delta: +%.1f%%)",
            tool.tool_name,
            self.claw_role,
            tool.performance_delta,
        )
        return True

    def disable(self, tool_name: str) -> bool:
        """Disable a deployed tool (keeps it in registry for re-enablement)."""
        if tool_name not in self._tools:
            logger.warning("Tool '%s' not found in registry", tool_name)
            return False

        self._tools[tool_name].status = "disabled"
        self._save()
        logger.info("Disabled tool '%s'", tool_name)
        return True

    def enable(self, tool_name: str) -> bool:
        """Re-enable a previously disabled tool."""
        if tool_name not in self._tools:
            logger.warning("Tool '%s' not found in registry", tool_name)
            return False

        self._tools[tool_name].status = "deployed"
        self._save()
        logger.info("Enabled tool '%s'", tool_name)
        return True

    def remove(self, tool_name: str) -> bool:
        """Permanently remove a tool from the registry."""
        if tool_name not in self._tools:
            return False
        del self._tools[tool_name]
        if tool_name in self._provenances:
            del self._provenances[tool_name]
        if tool_name in self._rollback_monitoring:
            del self._rollback_monitoring[tool_name]
        self._save()
        logger.info("Removed tool '%s'", tool_name)
        return True

    def get(self, tool_name: str) -> BuiltTool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def get_provenance(self, tool_name: str) -> ToolProvenance | None:
        """Get provenance for a tool."""
        return self._provenances.get(tool_name)

    def list_tools(self, status_filter: str | None = None) -> list[BuiltTool]:
        """List tools, optionally filtered by status."""
        tools = list(self._tools.values())
        if status_filter:
            tools = [t for t in tools if t.status == status_filter]
        return sorted(tools, key=lambda t: t.built_at)

    def count(self, status_filter: str | None = None) -> int:
        """Count tools, optionally filtered by status."""
        return len(self.list_tools(status_filter))

    def get_inventory(self) -> dict[str, Any]:
        """
        Get the full tool inventory as a dict (for blueprint embedding).

        Returns a dict mapping tool names to their metadata,
        suitable for inclusion in a BlueprintSnapshot.
        """
        inventory = {}
        for name, tool in self._tools.items():
            inventory[name] = {
                "name": tool.tool_name,
                "type": tool.tool_type,
                "version": tool.version,
                "performance_delta": tool.performance_delta,
                "training_data_hash": tool.training_data_hash,
                "status": tool.status,
                "built_at": tool.built_at,
            }
            if name in self._provenances:
                inventory[name]["provenance"] = self._provenances[name].to_dict()
        return inventory

    # ── Provenance Signing ─────────────────────────────────────────────

    def _create_provenance(self, tool: BuiltTool) -> ToolProvenance | None:
        """
        Create and sign provenance for a tool.

        Signs using squad private key from provenance-keygen.
        """
        provenance = ToolProvenance(
            tool_id=tool.tool_name,
            claw_role=tool.claw_role,
            generated_at=datetime.now(timezone.utc).isoformat(),
            generation_model="local-nim",
            trigger_pattern=str(tool.proposal.trigger_pattern.pattern_type)
            if tool.proposal
            else "",
            backtest_result={
                "baseline_score": tool.baseline_score,
                "tool_score": tool.tool_score,
                "improvement_pct": tool.performance_delta,
            },
            deployed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Sign the provenance
        if PROVENANCE_AVAILABLE and load_key_pair:
            try:
                key_data = load_key_pair(self.squad_id)
                if key_data:
                    private_key_bytes, public_key_bytes = key_data
                    signature = self._sign_provenance(provenance, private_key_bytes)
                    provenance.signature = signature
                    provenance.signer_key_id = public_key_bytes[:8].hex()
                    logger.info("Signed provenance for tool '%s'", tool.tool_name)
                else:
                    logger.warning("No signing key found for squad %s", self.squad_id)
            except Exception as e:
                logger.warning("Failed to sign provenance: %s", e)

        return provenance

    def _sign_provenance(
        self, provenance: ToolProvenance, private_key_bytes: bytes
    ) -> str:
        """Sign provenance data with Ed25519 private key."""
        if not PROVENANCE_AVAILABLE:
            return ""

        # Create content to sign
        content = json.dumps(provenance.to_dict(), sort_keys=True)

        # Load private key and sign
        private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = private_key.sign(content.encode())

        return signature.hex()

    def verify_provenance(self, tool_name: str) -> bool:
        """
        Verify tool provenance signature.

        Returns True if signature is valid or no signature present.
        Returns False if signature is invalid.
        """
        if tool_name not in self._provenances:
            return True  # No provenance to verify

        provenance = self._provenances[tool_name]

        if not provenance.signature:
            return True  # Unsigned provenance is allowed

        if not PROVENANCE_AVAILABLE or not load_key_pair:
            logger.warning("Cannot verify signature: cryptography not available")
            return True

        try:
            key_data = load_key_pair(self.squad_id)
            if not key_data:
                logger.warning("No public key found for verification")
                return False

            _, public_key_bytes = key_data

            # Reconstruct content that was signed
            unsigned_provenance = ToolProvenance(
                tool_id=provenance.tool_id,
                claw_role=provenance.claw_role,
                generated_at=provenance.generated_at,
                generation_model=provenance.generation_model,
                trigger_pattern=provenance.trigger_pattern,
                backtest_result=provenance.backtest_result,
                deployed_at=provenance.deployed_at,
            )
            content = json.dumps(unsigned_provenance.to_dict(), sort_keys=True)

            # Verify signature
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            signature = bytes.fromhex(provenance.signature)
            public_key.verify(signature, content.encode())

            return True

        except InvalidSignature:
            logger.warning("Invalid signature for tool '%s'", tool_name)
            return False
        except Exception as e:
            logger.warning("Provenance verification error: %s", e)
            return False

    # ── Rollback Detection ─────────────────────────────────────────────

    def check_for_regression(
        self,
        tool_name: str,
        current_metric_value: float,
    ) -> RollbackDecision:
        """
        Check if tool is causing regression.

        Monitors target metric for 7 days post-deploy.
        If metric < baseline * 0.95: deactivates tool.

        Args:
            tool_name: Tool to check
            current_metric_value: Current value of target metric

        Returns:
            RollbackDecision with should_rollback flag
        """
        if tool_name not in self._tools:
            return RollbackDecision(
                should_rollback=False,
                tool_name=tool_name,
                reason="Tool not found",
                current_metric=current_metric_value,
                baseline_metric=0.0,
                threshold=0.95,
                days_since_deploy=0,
            )

        if tool_name not in self._rollback_monitoring:
            return RollbackDecision(
                should_rollback=False,
                tool_name=tool_name,
                reason="Not in monitoring",
                current_metric=current_metric_value,
                baseline_metric=0.0,
                threshold=0.95,
                days_since_deploy=0,
            )

        monitoring = self._rollback_monitoring[tool_name]
        tool = self._tools[tool_name]

        # Calculate days since deployment
        deployed_at = datetime.fromisoformat(monitoring["deployed_at"])
        days_since = (datetime.now(timezone.utc) - deployed_at).days

        # Only monitor for 7 days
        if days_since > 7:
            return RollbackDecision(
                should_rollback=False,
                tool_name=tool_name,
                reason="Monitoring period ended",
                current_metric=current_metric_value,
                baseline_metric=monitoring["baseline_metric"],
                threshold=monitoring["threshold"],
                days_since_deploy=days_since,
            )

        baseline = monitoring["baseline_metric"]
        threshold = monitoring["threshold"]
        minimum_acceptable = baseline * threshold

        if current_metric_value < minimum_acceptable:
            # Regression detected - deactivate tool
            tool.status = "rolled_back"
            self._save()

            logger.warning(
                "Tool '%s' rolled back: metric %.2f < %.2f (threshold)",
                tool_name,
                current_metric_value,
                minimum_acceptable,
            )

            return RollbackDecision(
                should_rollback=True,
                tool_name=tool_name,
                reason=f"Metric {current_metric_value:.2f} below threshold {minimum_acceptable:.2f}",
                current_metric=current_metric_value,
                baseline_metric=baseline,
                threshold=threshold,
                days_since_deploy=days_since,
            )

        # Record check
        monitoring["checks"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": current_metric_value,
            }
        )

        return RollbackDecision(
            should_rollback=False,
            tool_name=tool_name,
            reason="Metric within bounds",
            current_metric=current_metric_value,
            baseline_metric=baseline,
            threshold=threshold,
            days_since_deploy=days_since,
        )

    # ── Persistence ───────────────────────────────────────────────────

    def _save(self) -> None:
        """Persist the registry to disk."""
        if self._memory_only:
            return
        data = {
            "squad_id": self.squad_id,
            "claw_role": self.claw_role,
            "tool_count": len(self._tools),
            "tools": {name: tool.to_dict() for name, tool in self._tools.items()},
            "provenances": {
                name: prov.to_dict() for name, prov in self._provenances.items()
            },
            "rollback_monitoring": self._rollback_monitoring,
        }
        with self._registry_file.open("w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        """Load the registry from disk."""
        if not self._registry_file.exists():
            return

        try:
            with self._registry_file.open() as f:
                data = json.load(f)

            for name, tool_data in data.get("tools", {}).items():
                self._tools[name] = BuiltTool.from_dict(tool_data)

            for name, prov_data in data.get("provenances", {}).items():
                self._provenances[name] = ToolProvenance.from_dict(prov_data)

            self._rollback_monitoring = data.get("rollback_monitoring", {})

            # Verify all signatures on load
            for tool_name in list(self._tools.keys()):
                if not self.verify_provenance(tool_name):
                    logger.warning(
                        "Tool '%s' has invalid signature - skipping",
                        tool_name,
                    )

            logger.info(
                "Loaded %d tools from registry for %s",
                len(self._tools),
                self.claw_role,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load registry: %s", e)
            self._tools = {}

    def clear(self) -> None:
        """Clear all tools (for testing)."""
        self._tools = {}
        self._provenances = {}
        self._rollback_monitoring = {}
        if self._registry_file.exists():
            self._registry_file.unlink()
