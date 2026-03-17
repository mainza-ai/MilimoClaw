#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Milimo Blueprint Marketplace and Merging logic.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from orchestrator.blueprint_manager import BlueprintManager, BlueprintSnapshot, BlueprintMeta
from orchestrator.marketplace_manager import MarketplaceManager
from orchestrator.blueprint_merger import BlueprintMerger


class TestBlueprintMarketplace(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.marketplace_dir = self.test_dir / "marketplace"
        self.blueprints_dir = self.test_dir / "local_blueprints"
        self.blueprints_dir.mkdir()
        
        # Initialize managers
        self.market = MarketplaceManager(marketplace_dir=str(self.marketplace_dir))
        self.mgr = BlueprintManager(
            squad_id="test-squad",
            claw_role="content",
            blueprint_dir=str(self.blueprints_dir),
            versions_dir=str(self.test_dir / "versions")
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_publish_and_search(self):
        # Create a mock snapshot
        snapshot = self.mgr.export(niche_tags=["test", "demo"])
        
        # Publish
        bp_id = self.market.publish(snapshot, "free", "Test Blueprint", "test-squad")
        self.assertIn("@test-squad/test-blueprint", bp_id)
        
        # Search
        results = self.market.search(query="test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], bp_id)
        
        # Get listing
        listing = self.market.get_listing(bp_id)
        self.assertIsNotNone(listing)
        self.assertEqual(listing["price"], "free")

    def test_merge_logic(self):
        # Base snapshot with one tool
        base_snap = self.mgr.export()
        base_snap.tools_inventory = {"tool_a": {"version": "1.0"}}
        base_snap.policy = {"allow_eval": True, "threshold": 0.5}
        
        # Incoming snapshot with another tool and stricter policy
        incoming_snap = self.mgr.export()
        incoming_snap.meta.version = "0.2.0"
        incoming_snap.tools_inventory = {"tool_b": {"version": "2.0"}}
        incoming_snap.policy = {"allow_eval": False, "threshold": 0.8}
        
        # Merge
        merged = BlueprintMerger.merge(base_snap, incoming_snap)
        
        # Verify tools (union)
        self.assertIn("tool_a", merged.tools_inventory)
        self.assertIn("tool_b", merged.tools_inventory)
        
        # Verify policy (restrictive)
        self.assertFalse(merged.policy["allow_eval"])  # False overrides True
        self.assertEqual(merged.policy["threshold"], 0.8)  # Max threshold (stricter)

    def test_provenance(self):
        snapshot = self.mgr.export()
        self.assertTrue(self.mgr.verify_integrity(snapshot))
        self.assertTrue(self.mgr.verify_provenance(snapshot))


if __name__ == "__main__":
    unittest.main()
