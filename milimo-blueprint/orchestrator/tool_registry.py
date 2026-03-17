#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Tool Registry

Manages the inventory of all evolved tools for a claw. Each claw
has its own registry at ~/.milimo/tools/<squadId>/<role>/registry.json.

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
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .tool_builder import BuiltTool

logger = logging.getLogger("milimo.tool_registry")


class ToolRegistry:
    """
    Manages the inventory of evolved tools for a single claw.

    Supports registration, enable/disable, listing, and persistence.
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
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._dir = Path(home) / ".milimo" / "tools" / squad_id / claw_role

        self._dir.mkdir(parents=True, exist_ok=True)
        self._registry_file = self._dir / "registry.json"
        self._tools: dict[str, BuiltTool] = {}
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
        self._save()
        logger.info("Removed tool '%s'", tool_name)
        return True

    def get(self, tool_name: str) -> BuiltTool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

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
        return inventory

    # ── Persistence ───────────────────────────────────────────────────

    def _save(self) -> None:
        """Persist the registry to disk."""
        data = {
            "squad_id": self.squad_id,
            "claw_role": self.claw_role,
            "tool_count": len(self._tools),
            "tools": {name: tool.to_dict() for name, tool in self._tools.items()},
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
        if self._registry_file.exists():
            self._registry_file.unlink()
