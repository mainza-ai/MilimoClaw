# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Blueprint Marketplace Manager

A simulated peer-to-peer registry for publishing, discovering, and downloading
blueprints.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .blueprint_manager import BlueprintSnapshot

logger = logging.getLogger("milimo.marketplace_manager")


class MarketplaceManager:
    """Manages interactions with the public blueprint marketplace."""

    def __init__(self, marketplace_dir: Optional[str] = None):
        if marketplace_dir:
            self._dir = Path(marketplace_dir)
        else:
            home = os.environ.get("HOME", os.environ.get("USERPROFILE", "/tmp"))
            self._dir = Path(home) / ".milimo" / "marketplace"

        self._registry_file = self._dir / "registry.json"
        self._blueprints_dir = self._dir / "blueprints"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._blueprints_dir.mkdir(parents=True, exist_ok=True)

        self._ensure_registry()

    def _ensure_registry(self) -> None:
        """Ensure the registry index file exists."""
        if not self._registry_file.exists():
            with self._registry_file.open("w") as f:
                json.dump({"listings": {}}, f, indent=2)

    def _load_registry(self) -> Dict[str, Any]:
        """Load the full marketplace registry index."""
        try:
            with self._registry_file.open("r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"listings": {}}

    def _save_registry(self, registry: Dict[str, Any]) -> None:
        """Save the marketplace registry index."""
        with self._registry_file.open("w") as f:
            json.dump(registry, f, indent=2, default=str)

    def publish(
        self, snapshot: BlueprintSnapshot, price: str, name: str, squad_id: str
    ) -> str:
        """
        List a blueprint on the public registry.
        Returns the marketplace blueprint ID.
        """
        registry = self._load_registry()

        # Generate unique ID based on name and timestamp
        datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        safe_name = "".join(c if c.isalnum() else "-" for c in name).lower().strip("-")
        blueprint_id = f"@{squad_id}/{safe_name}-v{snapshot.meta.version}"

        # Write snapshot artifact securely
        snapshot_path = self._blueprints_dir / f"{blueprint_id.replace('/', '_')}.json"
        with snapshot_path.open("w") as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)

        tool_count = len(snapshot.tools_inventory.keys())

        # Update registry listing
        registry["listings"][blueprint_id] = {
            "id": blueprint_id,
            "name": name,
            "business_type": snapshot.meta.business_type,
            "version": snapshot.meta.version,
            "author": squad_id,
            "price": price,
            "tags": snapshot.meta.niche_tags,
            "tool_count": tool_count,
            "fork_count": 0,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "verified": bool(snapshot.integrity.get("digest")),
        }

        self._save_registry(registry)
        logger.info(f"Published blueprint {blueprint_id} to marketplace for {price}")
        return blueprint_id

    def search(self, query: str = "", category: str = "") -> List[Dict[str, Any]]:
        """
        Discover blueprints by query matched against name/tags/author,
        and optionally filtered by business type category.
        """
        registry = self._load_registry()
        listings = registry.get("listings", {}).values()

        results = []
        for listing in listings:
            if (
                category
                and listing.get("business_type", "").lower() != category.lower()
            ):
                continue

            if query:
                q = query.lower()
            matches_query = (
                q in listing.get("name", "").lower()
                or q in listing.get("author", "").lower()
                or any(q in tag.lower() for tag in listing.get("tags", []))
            )
            if not matches_query:
                continue

        results.append(listing)

        # Sort by verified and fork count
        results.sort(
            key=lambda x: (x.get("verified", False), x.get("fork_count", 0)),
            reverse=True,
        )
        return results

    def get_listing(self, blueprint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a single blueprint listing."""
        registry = self._load_registry()
        return registry.get("listings", {}).get(blueprint_id)

    def download(self, blueprint_id: str) -> Optional[BlueprintSnapshot]:
        """
        Download a blueprint snapshot from the marketplace.
        Also increments the fork count.
        """
        registry = self._load_registry()
        if blueprint_id not in registry.get("listings", {}):
            logger.error(f"Blueprint {blueprint_id} not found in marketplace.")
            return None

        snapshot_path = self._blueprints_dir / f"{blueprint_id.replace('/', '_')}.json"
        if not snapshot_path.exists():
            logger.error(f"Blueprint artifact for {blueprint_id} is missing.")
            return None

        # Increment fork count
        registry["listings"][blueprint_id]["fork_count"] = (
            registry["listings"][blueprint_id].get("fork_count", 0) + 1
        )
        self._save_registry(registry)

        with snapshot_path.open() as f:
            data = json.load(f)

        logger.info(f"Downloaded blueprint {blueprint_id} from marketplace.")
        return BlueprintSnapshot.from_dict(data)
