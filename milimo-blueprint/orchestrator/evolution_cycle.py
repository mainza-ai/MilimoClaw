# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Evolution Cycle

The main orchestrator for the weekly self-evolution cycle. Runs the
5-stage pipeline for a single claw:

    1. OBSERVE   → Read the operation log for the past 7 days
    2. IDENTIFY  → Surface recurring patterns
    3. PROPOSE   → Nominate a tool to address the strongest pattern
    4. BUILD     → Generate tool code and backtest in sandbox
    5. DEPLOY    → Activate, version the blueprint, notify War Room

Each cycle produces at most 1 tool. The cycle runs weekly by default,
or can be triggered manually.

Usage:
    from evolution_cycle import EvolutionCycle, EvolutionScheduler

    cycle = EvolutionCycle(
        squad_id="my-squad",
        claw_role="content",
        blueprint_dir="/path/to/milimo-blueprint",
    )
    result = cycle.run()

    scheduler = EvolutionScheduler()
    scheduler.register(cycle)
    scheduler.start()  # runs weekly
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .operation_log import OperationLog
from .pattern_detector import PatternDetector
from .tool_builder import BuildResult, BuiltTool, ToolBuilder
from .tool_proposal import (
    ToolProposal,
    generate_proposal,
    load_sandbox_policy,
    validate_permissions,
)
from .tool_registry import ToolRegistry

logger = logging.getLogger("milimo.evolution_cycle")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EvolutionConfig:
    """Configuration loaded from evolution_config.yaml."""

    cycle_interval_days: int = 7
    window_days: int = 7
    minimum_actions: int = 20
    cross_signal_lookback_days: int = 14
    min_confidence: float = 0.6
    max_patterns: int = 5
    backtest_window_weeks: int = 4
    min_improvement_percent: float = 5.0
    max_tools_per_claw: int = 30
    require_proposal_approval: bool = False
    notify_war_room: bool = True

    @classmethod
    def from_file(cls, path: str | Path) -> EvolutionConfig:
        """Load configuration from YAML file."""
        p = Path(path)
        if not p.exists():
            logger.warning("Evolution config not found at %s, using defaults", p)
            return cls()

        with p.open() as f:
            data = yaml.safe_load(f) or {}

        schedule = data.get("schedule", {})
        observation = data.get("observation", {})
        detection = data.get("detection", {})
        building = data.get("building", {})
        deployment = data.get("deployment", {})
        log_config = data.get("logging", {})

        return cls(
            cycle_interval_days=schedule.get("cycle_interval_days", 7),
            window_days=observation.get("window_days", 7),
            minimum_actions=observation.get("minimum_actions", 20),
            cross_signal_lookback_days=observation.get(
                "cross_signal_lookback_days", 14
            ),
            min_confidence=detection.get("minimum_confidence", 0.6),
            max_patterns=detection.get("max_patterns_per_cycle", 5),
            backtest_window_weeks=building.get("backtest_window_weeks", 4),
            min_improvement_percent=building.get("minimum_improvement_percent", 5.0),
            max_tools_per_claw=deployment.get("max_tools_per_claw", 30),
            require_proposal_approval=deployment.get(
                "require_proposal_approval", False
            ),
            notify_war_room=log_config.get("notify_war_room", True),
        )


@dataclass
class CycleResult:
    """Result of a single evolution cycle."""

    claw_role: str
    squad_id: str
    stage_reached: str  # observe | identify | propose | build | deploy
    patterns_found: int = 0
    proposal: ToolProposal | None = None
    build_result: BuildResult | None = None
    tool_deployed: BuiltTool | None = None
    skipped_reason: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        d = {
            "claw_role": self.claw_role,
            "squad_id": self.squad_id,
            "stage_reached": self.stage_reached,
            "patterns_found": self.patterns_found,
            "skipped_reason": self.skipped_reason,
            "timestamp": self.timestamp,
        }
        if self.proposal:
            d["proposal"] = self.proposal.to_dict()
        if self.tool_deployed:
            d["tool_deployed"] = self.tool_deployed.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CycleResult":
        proposal = None
        if data.get("proposal"):
            try:
                proposal = ToolProposal.from_dict(data["proposal"])
            except Exception:
                pass
        tool_deployed = None
        if data.get("tool_deployed"):
            try:
                tool_deployed = BuiltTool.from_dict(data["tool_deployed"])
            except Exception:
                pass
        return cls(
            claw_role=data.get("claw_role", ""),
            squad_id=data.get("squad_id", ""),
            stage_reached=data.get("stage_reached", ""),
            patterns_found=data.get("patterns_found", 0),
            proposal=proposal,
            build_result=None,
            tool_deployed=tool_deployed,
            skipped_reason=data.get("skipped_reason", ""),
            timestamp=data.get("timestamp", ""),
        )


# ---------------------------------------------------------------------------
# Evolution Cycle
# ---------------------------------------------------------------------------


class EvolutionCycle:
    """
    Orchestrates the 5-stage weekly evolution cycle for a single claw.

    Stages:
        1. OBSERVE   — Read the operation log
        2. IDENTIFY  — Detect patterns
        3. PROPOSE   — Generate a tool proposal
        4. BUILD     — Build and backtest
        5. DEPLOY    — Activate and version
    """

    def __init__(
        self,
        squad_id: str,
        claw_role: str,
        blueprint_dir: str | Path,
        log_dir: str | None = None,
        registry_dir: str | None = None,
        config: EvolutionConfig | None = None,
        inference_client: Any | None = None,
    ) -> None:
        self.squad_id = squad_id
        self.claw_role = claw_role
        self.blueprint_dir = Path(blueprint_dir)

        # Load evolution configuration
        if config:
            self.config = config
        else:
            config_path = self.blueprint_dir / "evolution_config.yaml"
            self.config = EvolutionConfig.from_file(config_path)

        # Initialize components
        self.operation_log = OperationLog(
            squad_id=squad_id,
            claw_role=claw_role,
            log_dir=log_dir,
        )
        self.pattern_detector = PatternDetector(
            claw_role=claw_role,
            min_confidence=self.config.min_confidence,
            max_patterns=self.config.max_patterns,
        )
        self.tool_builder = ToolBuilder(
            claw_role=claw_role,
            squad_id=squad_id,
            min_improvement_percent=self.config.min_improvement_percent,
            backtest_window_weeks=self.config.backtest_window_weeks,
            inference_client=inference_client,
        )
        self.tool_registry = ToolRegistry(
            squad_id=squad_id,
            claw_role=claw_role,
            registry_dir=registry_dir,
            max_tools=self.config.max_tools_per_claw,
        )

    def run(self, dry_run: bool = False) -> CycleResult:
        """
        Execute the full evolution cycle.

        Args:
            dry_run: If True, run stages 1–3 only (no build or deploy).

        Returns:
            CycleResult describing what happened.
        """
        logger.info(
            "Starting evolution cycle for %s in squad %s%s",
            self.claw_role,
            self.squad_id,
            " (DRY RUN)" if dry_run else "",
        )

        # ── Stage 1: OBSERVE ──────────────────────────────────────────
        actions = self.operation_log.get_window(days=self.config.window_days)
        if len(actions) < self.config.minimum_actions:
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="observe",
                skipped_reason=(
                    f"Insufficient data: {len(actions)} actions "
                    f"(need {self.config.minimum_actions})"
                ),
            )

        summary = self.operation_log.get_action_summary(actions)
        cross_signals = self.operation_log.get_cross_signals(
            days=self.config.cross_signal_lookback_days
        )

        logger.info(
            "Stage 1 OBSERVE: %d actions, %d cross-signals",
            len(actions),
            len(cross_signals),
        )

        # ── Stage 2: IDENTIFY ─────────────────────────────────────────
        patterns = self.pattern_detector.detect(summary, actions, cross_signals)
        best_pattern = self.pattern_detector.rank(patterns)

        if best_pattern is None:
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="identify",
                patterns_found=len(patterns),
                skipped_reason="No patterns above confidence threshold",
            )

        logger.info(
            "Stage 2 IDENTIFY: %d patterns found, best: %s (%.2f confidence)",
            len(patterns),
            best_pattern.pattern_type,
            best_pattern.confidence,
        )

        # ── Stage 3: PROPOSE ──────────────────────────────────────────
        proposal = generate_proposal(
            pattern=best_pattern,
            claw_role=self.claw_role,
            squad_id=self.squad_id,
        )

        # Validate permissions
        policy_path = self.blueprint_dir / "policies" / f"{self.claw_role}-sandbox.yaml"
        if policy_path.exists():
            policy = load_sandbox_policy(policy_path)
            valid, reason = validate_permissions(proposal, policy)
            if not valid:
                proposal.status = "rejected"
                proposal.rejection_reason = reason
                return CycleResult(
                    claw_role=self.claw_role,
                    squad_id=self.squad_id,
                    stage_reached="propose",
                    patterns_found=len(patterns),
                    proposal=proposal,
                    skipped_reason=f"Permission check failed: {reason}",
                )

        logger.info(
            "Stage 3 PROPOSE: '%s' (%s) — estimated +%.1f%% on %s",
            proposal.tool_name,
            proposal.tool_type,
            proposal.estimated_improvement,
            proposal.metric_target,
        )

        if dry_run:
            proposal.status = "proposed"
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="propose",
                patterns_found=len(patterns),
                proposal=proposal,
                skipped_reason="Dry run — stopped after propose stage",
            )

        # Check if approval is required
        if self.config.require_proposal_approval:
            proposal.status = "proposed"
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="propose",
                patterns_found=len(patterns),
                proposal=proposal,
                skipped_reason="Awaiting squad approval for proposal",
            )

        # ── Stage 4: BUILD & TEST ─────────────────────────────────────
        # Get historical actions for backtesting
        backtest_days = self.config.backtest_window_weeks * 7
        historical = self.operation_log.get_window(days=backtest_days)

        build_result = self.tool_builder.build(
            proposal=proposal,
            historical_actions=historical,
        )

        if not build_result.passed:
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="build",
                patterns_found=len(patterns),
                proposal=proposal,
                build_result=build_result,
                skipped_reason=build_result.failure_reason,
            )

        logger.info(
            "Stage 4 BUILD: tool '%s' passed backtest (+%.1f%%)",
            proposal.tool_name,
            build_result.backtest.improvement_percent if build_result.backtest else 0,
        )

        # ── Stage 5: DEPLOY ───────────────────────────────────────────
        tool = build_result.tool
        if tool is None:
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="build",
                patterns_found=len(patterns),
                proposal=proposal,
                skipped_reason="Build produced no tool",
            )

        # Register in the tool registry
        registered = self.tool_registry.register(tool)
        if not registered:
            return CycleResult(
                claw_role=self.claw_role,
                squad_id=self.squad_id,
                stage_reached="deploy",
                patterns_found=len(patterns),
                proposal=proposal,
                build_result=build_result,
                skipped_reason="Tool registry at capacity",
            )

        # Stage for deployment
        self.tool_builder.stage_for_deployment(tool)

        logger.info(
            "Stage 5 DEPLOY: tool '%s' deployed to %s (delta: +%.1f%%)",
            tool.tool_name,
            self.claw_role,
            tool.performance_delta,
        )

        return CycleResult(
            claw_role=self.claw_role,
            squad_id=self.squad_id,
            stage_reached="deploy",
            patterns_found=len(patterns),
            proposal=proposal,
            build_result=build_result,
            tool_deployed=tool,
        )


# ---------------------------------------------------------------------------
# Evolution Scheduler
# ---------------------------------------------------------------------------


_STATE_DIR = Path("/sandbox/.openclaw/milimo/state")
_EVOLUTION_DIR = _STATE_DIR / "evolution"
_HISTORY_FILE = _EVOLUTION_DIR / "history.jsonl"
_SUMMARY_FILE = _EVOLUTION_DIR / "summary.json"


def _load_history() -> list[dict[str, Any]]:
    if not _HISTORY_FILE.exists():
        return []
    results = []
    with _HISTORY_FILE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def _save_summary(summary: dict[str, Any]) -> None:
    _EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    with _SUMMARY_FILE.open("w") as f:
        json.dump(summary, f, indent=2, default=str)


class EvolutionScheduler:
    """
    Manages weekly evolution scheduling for all claws in a squad.

    In production, this would use a timer or cron-like mechanism.
    For now, provides manual trigger and status.
    """

    def __init__(self) -> None:
        self._cycles: dict[str, EvolutionCycle] = {}
        loaded = _load_history()
        self._history: list[CycleResult] = [CycleResult.from_dict(d) for d in loaded]

    def register(self, cycle: EvolutionCycle) -> None:
        """Register a claw's evolution cycle."""
        self._cycles[cycle.claw_role] = cycle
        logger.info("Registered evolution cycle for %s", cycle.claw_role)

    def unregister(self, claw_role: str) -> None:
        """Unregister a claw's evolution cycle."""
        self._cycles.pop(claw_role, None)

    def trigger(
        self, claw_role: str | None = None, dry_run: bool = False
    ) -> list[CycleResult]:
        """
        Manually trigger evolution cycles.

        Args:
            claw_role: If specified, only run for this claw.
                       If None, run for all registered claws.
            dry_run: If True, run stages 1–3 only.

        Returns:
            List of CycleResults.
        """
        results: list[CycleResult] = []

        if claw_role:
            if claw_role not in self._cycles:
                logger.warning("No evolution cycle registered for %s", claw_role)
                return results
            cycles = {claw_role: self._cycles[claw_role]}
        else:
            cycles = dict(self._cycles)

        for role, cycle in cycles.items():
            try:
                result = cycle.run(dry_run=dry_run)
                results.append(result)
                self._history.append(result)
                self._append_history(result.to_dict())
                self._update_summary()
            except Exception as e:
                logger.error("Evolution cycle failed for %s: %s", role, e)
                results.append(
                    CycleResult(
                        claw_role=role,
                        squad_id=cycle.squad_id,
                        stage_reached="error",
                        skipped_reason=str(e),
                    )
                )

        return results

    def _append_history(self, cycle_dict: dict[str, Any]) -> None:
        _EVOLUTION_DIR.mkdir(parents=True, exist_ok=True)
        with _HISTORY_FILE.open("a") as f:
            f.write(json.dumps(cycle_dict, default=str) + "\n")

    def _update_summary(self) -> None:
        by_role: dict[str, dict[str, Any]] = {}
        for entry in reversed(self._history):
            role = getattr(entry, "claw_role", "")
            if role and role not in by_role:
                by_role[role] = {
                    "claw_role": role,
                    "last_run": getattr(entry, "timestamp", None),
                    "last_stage": getattr(entry, "stage_reached", None),
                    "last_skipped_reason": getattr(entry, "skipped_reason", "") or None,
                    "tools_deployed": sum(
                        1
                        for e in self._history
                        if getattr(e, "claw_role", "") == role
                        and getattr(e, "tool_deployed", None) is not None
                    ),
                }
        _save_summary(
            {
                "total_cycles": len(self._history),
                "registered_claws": list(self._cycles.keys()),
                "by_role": by_role,
            }
        )

    def get_history(self, limit: int = 10) -> list[CycleResult]:
        """Get the most recent cycle results."""
        return self._history[-limit:]

    def get_status(self) -> dict[str, Any]:
        """Get the current scheduler status."""
        return {
            "registered_claws": list(self._cycles.keys()),
            "total_cycles_run": len(self._history),
            "last_run": self._history[-1].timestamp if self._history else None,
        }
