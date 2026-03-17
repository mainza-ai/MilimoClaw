#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Blueprint Merger

Handles combining two blueprint snapshots, resolving tool conflicts,
and applying restrictive policy merges.
"""

import copy
import logging
from typing import Any, Dict

from .blueprint_manager import BlueprintSnapshot

logger = logging.getLogger("milimo.blueprint_merger")


class BlueprintMerger:
    """Merges two blueprint snapshots."""

    @staticmethod
    def merge(base: BlueprintSnapshot, incoming: BlueprintSnapshot) -> BlueprintSnapshot:
        """
        Merge incoming blueprint into the base blueprint.
        Returns a new merged blueprint snapshot (without integrity digest).
        """
        merged_tools = BlueprintMerger._merge_tools(base.tools_inventory, incoming.tools_inventory)
        merged_policy = BlueprintMerger._merge_policies(base.policy, incoming.policy)
        merged_priors = BlueprintMerger._merge_priors(base.learned_priors, incoming.learned_priors)
        
        # Claw config mostly stays as base, but we can merge some non-conflicting keys
        merged_config = copy.deepcopy(base.claw_config)
        for k, v in incoming.claw_config.items():
            if k not in merged_config:
                merged_config[k] = copy.deepcopy(v)

        # Meta can be base meta + a note about being a merged blueprint
        merged_meta = copy.deepcopy(base.meta)
        merged_meta.niche_tags = list(set(base.meta.niche_tags + incoming.meta.niche_tags))
        
        snapshot = BlueprintSnapshot(
            meta=merged_meta,
            claw_config=merged_config,
            tools_inventory=merged_tools,
            policy=merged_policy,
            learned_priors=merged_priors,
        )
        
        logger.info(f"Merged blueprints. Base v{base.meta.version} + Incoming v{incoming.meta.version}")
        return snapshot

    @staticmethod
    def _merge_tools(base_tools: Dict[str, Any], incoming_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Combine tool inventories. On collision, incoming overrides base."""
        merged = copy.deepcopy(base_tools)
        for name, tool_data in incoming_tools.items():
            # If performance score exists, we could use the higher one, but for simplicity
            # we assume incoming is an evolution upgrade we want to apply.
            merged[name] = copy.deepcopy(tool_data)
        return merged

    @staticmethod
    def _merge_policies(base_policy: Dict[str, Any], incoming_policy: Dict[str, Any]) -> Dict[str, Any]:
        """Combine policies, taking the most restrictive settings."""
        merged = copy.deepcopy(base_policy)
        
        for k, v in incoming_policy.items():
            if k not in merged:
                merged[k] = copy.deepcopy(v)
                continue
                
            base_val = merged[k]
            
            # Simple restrictive logic based on naming / type
            if isinstance(base_val, bool) and isinstance(v, bool):
                # e.g., allow_eval: False overrides True
                merged[k] = base_val and v
            elif isinstance(base_val, (int, float)) and isinstance(v, (int, float)):
                # If metric looks like a threshold, take the max (stricter)
                if "threshold" in k.lower() or "limit" in k.lower():
                    merged[k] = min(base_val, v) if "limit" in k.lower() else max(base_val, v)
                else:
                    merged[k] = max(base_val, v)
            elif isinstance(base_val, list) and isinstance(v, list):
                # Intersect for allowed things, union for blocked things
                if "allow" in k.lower():
                    # Intersection of allowed routes/domains
                    merged[k] = list(set(base_val) & set(v))
                elif "block" in k.lower() or "deny" in k.lower():
                    # Union of blocked routes/domains
                    merged[k] = list(set(base_val) | set(v))
                else:
                    merged[k] = list(set(base_val + v))
            elif isinstance(base_val, dict) and isinstance(v, dict):
                merged[k] = BlueprintMerger._merge_policies(base_val, v)
                
        return merged

    @staticmethod
    def _merge_priors(base_priors: Dict[str, Any], incoming_priors: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate learned priors recursively."""
        merged = copy.deepcopy(base_priors)
        
        for k, v in incoming_priors.items():
            if k not in merged:
                merged[k] = copy.deepcopy(v)
            elif isinstance(merged[k], list) and isinstance(v, list):
                # Union of lists
                merged[k] = list(set(merged[k] + v))
            elif isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = BlueprintMerger._merge_priors(merged[k], v)
            else:
                # If string or primitive, keep base but maybe append if style
                if isinstance(merged[k], str) and isinstance(v, str):
                    if "style" in k.lower() or "pattern" in k.lower():
                        merged[k] = f"{merged[k]} | {v}"
                        
        return merged
