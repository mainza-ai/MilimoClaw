# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Milimo Claw Self-Evolution Engine.

Covers:
  - OperationLog: recording, retrieval, summary, cross-signals
  - PatternDetector: edit patterns, approval patterns, timing, drift, cross-signal
  - ToolProposal: schema, permission validation, proposal generation
  - ToolBuilder: build flow, backtest, baseline comparison
  - ToolRegistry: register, disable, enable, list, persist
  - BlueprintManager: version bumps, export, diff, rollback, integrity
  - EvolutionCycle: full 5-stage pipeline
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent to path for imports
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.operation_log import ActionRecord, CrossSignal, OperationLog
from orchestrator.pattern_detector import EvolutionPattern, PatternDetector
from orchestrator.tool_proposal import (
    ToolProposal,
    generate_proposal,
    validate_permissions,
)
from orchestrator.tool_builder import BuiltTool, ToolBuilder
from orchestrator.tool_registry import ToolRegistry
from orchestrator.blueprint_manager import BlueprintManager
from orchestrator.evolution_cycle import (
    EvolutionConfig,
    EvolutionCycle,
    EvolutionScheduler,
)


# ═══════════════════════════════════════════════════════════════════════
#  Test Fixtures
# ═══════════════════════════════════════════════════════════════════════


def _make_actions(
    count, action_type="social_post_draft", outcome="approved", metrics=None, edits=None
):
    """Generate a list of ActionRecords for testing."""
    actions = []
    for i in range(count):
        ts = (datetime.now(timezone.utc) - timedelta(hours=i * 2)).isoformat()
        actions.append(
            ActionRecord(
                action_type=action_type,
                outcome=outcome,
                edits=edits or {},
                metrics=metrics or {},
                timestamp=ts,
            )
        )
    return actions


def _make_policy():
    """Return a sample sandbox policy for testing."""
    return {
        "filesystem_policy": {
            "read_write": ["/sandbox/content", "/tmp"],
            "read_only": ["/sandbox/analytics/reports"],
        },
        "network_policies": {
            "social_api": {
                "endpoints": [
                    {"host": "api.twitter.com", "methods": ["POST"]},
                    {"host": "graph.instagram.com", "methods": ["POST"]},
                ],
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════
#  OperationLog Tests
# ═══════════════════════════════════════════════════════════════════════


class TestOperationLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = OperationLog(
            squad_id="test-squad",
            claw_role="content",
            log_dir=self.tmp,
        )

    def test_record_and_count(self):
        self.assertEqual(self.log.count(), 0)
        self.log.record(ActionRecord(action_type="draft", outcome="approved"))
        self.log.record(ActionRecord(action_type="post", outcome="auto"))
        self.assertEqual(self.log.count(), 2)

    def test_get_all(self):
        self.log.record(ActionRecord(action_type="draft", outcome="approved"))
        self.log.record(ActionRecord(action_type="post", outcome="rejected"))
        all_actions = self.log.get_all()
        self.assertEqual(len(all_actions), 2)
        self.assertEqual(all_actions[0].action_type, "draft")

    def test_get_window_filters_by_time(self):
        # Record one recent, one old
        self.log.record(
            ActionRecord(
                action_type="recent",
                outcome="approved",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.log.record(
            ActionRecord(
                action_type="old",
                outcome="approved",
                timestamp=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            )
        )
        window = self.log.get_window(days=7)
        self.assertEqual(len(window), 1)
        self.assertEqual(window[0].action_type, "recent")

    def test_action_summary_computes_rates(self):
        actions = (
            _make_actions(5, outcome="approved")
            + _make_actions(3, outcome="edited", edits={"tone": "hype → edu"})
            + _make_actions(2, outcome="rejected")
        )
        summary = self.log.get_action_summary(actions)
        self.assertEqual(summary.total_actions, 10)
        self.assertAlmostEqual(summary.approval_rate, 0.5)
        self.assertAlmostEqual(summary.edit_rate, 0.3)
        self.assertIn("tone", summary.common_edits)

    def test_action_summary_empty(self):
        summary = self.log.get_action_summary([])
        self.assertEqual(summary.total_actions, 0)
        self.assertEqual(summary.approval_rate, 0.0)

    def test_record_and_get_cross_signals(self):
        signal = CrossSignal(
            sender_role="analytics",
            signal_type="summary",
            data={"retention_rate": 0.85},
        )
        self.log.record_cross_signal(signal)
        signals = self.log.get_cross_signals(days=7)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].sender_role, "analytics")

    def test_clear_removes_files(self):
        self.log.record(ActionRecord(action_type="x", outcome="auto"))
        self.log.record_cross_signal(
            CrossSignal(sender_role="ops", signal_type="signal")
        )
        self.log.clear()
        self.assertEqual(self.log.count(), 0)
        self.assertEqual(len(self.log.get_cross_signals()), 0)

    def test_metric_averages(self):
        actions = [
            ActionRecord(
                action_type="post", outcome="auto", metrics={"engagement": 0.04}
            ),
            ActionRecord(
                action_type="post", outcome="auto", metrics={"engagement": 0.06}
            ),
        ]
        summary = self.log.get_action_summary(actions)
        self.assertAlmostEqual(summary.metric_averages["engagement"], 0.05)


# ═══════════════════════════════════════════════════════════════════════
#  PatternDetector Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPatternDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PatternDetector(claw_role="content", min_confidence=0.3)

    def test_detect_edit_patterns(self):
        """High edit frequency on a field should produce a classifier pattern."""
        actions = _make_actions(
            6, outcome="edited", edits={"tone": "hype → educational"}
        ) + _make_actions(4, outcome="approved")
        log = OperationLog("s", "c", log_dir=tempfile.mkdtemp())
        summary = log.get_action_summary(actions)
        patterns = self.detector.detect(summary, actions)
        classifiers = [p for p in patterns if p.pattern_type == "classifier"]
        self.assertTrue(len(classifiers) > 0)
        self.assertIn("tone", classifiers[0].details.get("edit_field", ""))

    def test_detect_approval_patterns(self):
        """Low approval rate for an action type should produce a predictor pattern."""
        actions = _make_actions(
            3, action_type="email", outcome="approved"
        ) + _make_actions(7, action_type="email", outcome="rejected")
        log = OperationLog("s", "c", log_dir=tempfile.mkdtemp())
        summary = log.get_action_summary(actions)
        patterns = self.detector.detect(summary, actions)
        predictors = [p for p in patterns if p.pattern_type == "predictor"]
        self.assertTrue(len(predictors) > 0)

    def test_detect_metric_drift(self):
        """High metric variance should produce an anomaly_detector pattern."""
        actions = []
        for v in [0.01, 0.02, 0.03, 0.1, 0.15, 0.2]:
            actions.append(
                ActionRecord(
                    action_type="post",
                    outcome="auto",
                    metrics={"engagement": v},
                )
            )
        log = OperationLog("s", "c", log_dir=tempfile.mkdtemp())
        summary = log.get_action_summary(actions)
        patterns = self.detector.detect(summary, actions)
        anomalies = [p for p in patterns if p.pattern_type == "anomaly_detector"]
        self.assertTrue(len(anomalies) > 0)

    def test_detect_cross_signal_patterns(self):
        """Multiple signals from a claw should produce a cross-signal predictor."""
        actions = _make_actions(5, outcome="approved")
        signals = [
            CrossSignal(
                sender_role="analytics",
                signal_type="summary",
                data={"retention": 0.8, "churn_rate": 0.02},
            ),
            CrossSignal(
                sender_role="analytics",
                signal_type="summary",
                data={"retention": 0.82, "churn_rate": 0.018},
            ),
            CrossSignal(
                sender_role="analytics",
                signal_type="signal",
                data={"peak_hour": 19, "audience_size": 1200},
            ),
        ]
        log = OperationLog("s", "c", log_dir=tempfile.mkdtemp())
        summary = log.get_action_summary(actions)
        patterns = self.detector.detect(summary, actions, signals)
        cross = [p for p in patterns if "analytics" in p.trigger_description.lower()]
        self.assertTrue(len(cross) > 0)

    def test_rank_returns_highest_confidence(self):
        patterns = [
            EvolutionPattern(
                pattern_type="classifier",
                trigger_description="a",
                metric_target="x",
                confidence=0.5,
            ),
            EvolutionPattern(
                pattern_type="optimizer",
                trigger_description="b",
                metric_target="y",
                confidence=0.9,
            ),
        ]
        best = self.detector.rank(patterns)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.confidence, 0.9)

    def test_rank_returns_none_for_empty(self):
        self.assertIsNone(self.detector.rank([]))

    def test_no_patterns_on_empty_summary(self):
        log = OperationLog("s", "c", log_dir=tempfile.mkdtemp())
        summary = log.get_action_summary([])
        patterns = self.detector.detect(summary, [])
        self.assertEqual(len(patterns), 0)


# ═══════════════════════════════════════════════════════════════════════
#  ToolProposal Tests
# ═══════════════════════════════════════════════════════════════════════


class TestToolProposal(unittest.TestCase):
    def test_generate_proposal_from_pattern(self):
        pattern = EvolutionPattern(
            pattern_type="classifier",
            trigger_description="tone edited 60% of the time",
            metric_target="approval_rate",
            confidence=0.8,
            details={"edit_field": "tone"},
        )
        proposal = generate_proposal(pattern, claw_role="content", squad_id="test")
        self.assertEqual(proposal.tool_type, "classifier")
        self.assertEqual(proposal.claw_role, "content")
        self.assertIn("tone", proposal.tool_name)
        self.assertGreater(proposal.estimated_improvement, 0)

    def test_validate_permissions_passes(self):
        proposal = ToolProposal(
            tool_name="test_tool",
            tool_type="classifier",
            trigger_pattern=EvolutionPattern(
                pattern_type="classifier",
                trigger_description="t",
                metric_target="x",
                confidence=0.8,
            ),
            metric_target="approval_rate",
            data_sources_required=["/sandbox/content/styles"],
        )
        valid, reason = validate_permissions(proposal, _make_policy())
        self.assertTrue(valid)

    def test_validate_permissions_rejects_unauthorized_mount(self):
        proposal = ToolProposal(
            tool_name="test_tool",
            tool_type="classifier",
            trigger_pattern=EvolutionPattern(
                pattern_type="classifier",
                trigger_description="t",
                metric_target="x",
                confidence=0.8,
            ),
            metric_target="x",
            data_sources_required=["/sandbox/finance/invoices"],
        )
        valid, reason = validate_permissions(proposal, _make_policy())
        self.assertFalse(valid)
        self.assertIn("finance", reason)

    def test_validate_permissions_rejects_invalid_type(self):
        proposal = ToolProposal(
            tool_name="test",
            tool_type="INVALID",
            trigger_pattern=EvolutionPattern(
                pattern_type="classifier",
                trigger_description="t",
                metric_target="x",
                confidence=0.5,
            ),
            metric_target="x",
        )
        valid, reason = validate_permissions(proposal, _make_policy())
        self.assertFalse(valid)

    def test_proposal_serialization(self):
        proposal = generate_proposal(
            EvolutionPattern(
                pattern_type="optimizer",
                trigger_description="timing",
                metric_target="engagement",
                confidence=0.7,
            ),
            claw_role="content",
        )
        d = proposal.to_dict()
        restored = ToolProposal.from_dict(d)
        self.assertEqual(restored.tool_name, proposal.tool_name)
        self.assertEqual(restored.tool_type, proposal.tool_type)


# ═══════════════════════════════════════════════════════════════════════
#  ToolBuilder Tests
# ═══════════════════════════════════════════════════════════════════════


class TestToolBuilder(unittest.TestCase):
    def setUp(self):
        self.builder = ToolBuilder(
            claw_role="content",
            squad_id="test",
            min_improvement_percent=5.0,
            staging_dir=tempfile.mkdtemp(),
        )

    def _make_proposal(self, confidence=0.8):
        return ToolProposal(
            tool_name="test_classifier",
            tool_type="classifier",
            trigger_pattern=EvolutionPattern(
                pattern_type="classifier",
                trigger_description="tone edited 60%",
                metric_target="approval_rate",
                confidence=confidence,
            ),
            metric_target="approval_rate",
            claw_role="content",
        )

    def test_build_with_passing_tool(self):
        proposal = self._make_proposal(confidence=0.8)
        actions = _make_actions(20, outcome="approved")
        result = self.builder.build(
            proposal=proposal,
            historical_actions=actions,
            tool_code="def apply(data): return data",
        )
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.tool)
        self.assertIsNotNone(result.backtest)
        assert result.backtest is not None
        self.assertGreater(result.backtest.improvement_percent, 0)

    def test_build_with_low_confidence_fails(self):
        """Very low confidence → tiny improvement → below threshold."""
        proposal = self._make_proposal(confidence=0.1)
        actions = _make_actions(20, outcome="approved")
        result = self.builder.build(
            proposal=proposal,
            historical_actions=actions,
            tool_code="def apply(data): return data",
        )
        self.assertFalse(result.passed)

    def test_build_with_no_data(self):
        proposal = self._make_proposal()
        result = self.builder.build(proposal=proposal, historical_actions=[])
        self.assertFalse(result.passed)

    def test_stage_for_deployment(self):
        proposal = self._make_proposal()
        actions = _make_actions(20, outcome="approved")
        result = self.builder.build(
            proposal=proposal,
            historical_actions=actions,
            tool_code="def apply(data): return data",
        )
        if result.tool:
            path = self.builder.stage_for_deployment(result.tool)
            self.assertTrue(path.exists())


# ═══════════════════════════════════════════════════════════════════════
#  ToolRegistry Tests
# ═══════════════════════════════════════════════════════════════════════


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.registry = ToolRegistry(
            squad_id="test",
            claw_role="content",
            registry_dir=self.tmp,
            max_tools=5,
        )

    def _make_tool(self, name="test_tool"):
        return BuiltTool(
            proposal=ToolProposal(
                tool_name=name,
                tool_type="classifier",
                trigger_pattern=EvolutionPattern(
                    pattern_type="classifier",
                    trigger_description="t",
                    metric_target="x",
                    confidence=0.8,
                ),
                metric_target="x",
            ),
            tool_name=name,
            tool_type="classifier",
            code="pass",
            performance_delta=12.5,
        )

    def test_register_and_list(self):
        tool = self._make_tool()
        self.assertTrue(self.registry.register(tool))
        self.assertEqual(self.registry.count(), 1)
        tools = self.registry.list_tools()
        self.assertEqual(tools[0].tool_name, "test_tool")

    def test_disable_and_enable(self):
        self.registry.register(self._make_tool())
        self.registry.disable("test_tool")
        self.assertEqual(self.registry.count("disabled"), 1)
        self.assertEqual(self.registry.count("deployed"), 0)
        self.registry.enable("test_tool")
        self.assertEqual(self.registry.count("deployed"), 1)

    def test_max_tools_enforced(self):
        for i in range(5):
            self.registry.register(self._make_tool(f"tool_{i}"))
        # 6th should fail
        self.assertFalse(self.registry.register(self._make_tool("tool_5")))

    def test_persistence(self):
        self.registry.register(self._make_tool())
        # Create new registry instance from same directory
        registry2 = ToolRegistry("test", "content", registry_dir=self.tmp)
        self.assertEqual(registry2.count(), 1)

    def test_get_inventory(self):
        self.registry.register(self._make_tool("style_descriptor"))
        inv = self.registry.get_inventory()
        self.assertIn("style_descriptor", inv)
        self.assertEqual(inv["style_descriptor"]["type"], "classifier")

    def test_remove_tool(self):
        self.registry.register(self._make_tool())
        self.assertTrue(self.registry.remove("test_tool"))
        self.assertEqual(self.registry.count(), 0)

    def test_disable_nonexistent_returns_false(self):
        self.assertFalse(self.registry.disable("nonexistent"))

    def test_clear(self):
        self.registry.register(self._make_tool())
        self.registry.clear()
        self.assertEqual(self.registry.count(), 0)


# ═══════════════════════════════════════════════════════════════════════
#  BlueprintManager Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBlueprintManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bp_dir = Path(self.tmp) / "milimo-blueprint"
        (self.bp_dir / "roles").mkdir(parents=True)
        (self.bp_dir / "policies").mkdir(parents=True)

        # Write a minimal role config
        with (self.bp_dir / "roles" / "content-claw.yaml").open("w") as f:
            f.write("role: content\ndisplay_name: Content Claw\n")

        # Write a minimal policy
        with (self.bp_dir / "policies" / "content-sandbox.yaml").open("w") as f:
            f.write("filesystem_policy:\n  read_write:\n    - /sandbox/content\n")

        self.versions_dir = os.path.join(self.tmp, "versions")
        self.manager = BlueprintManager(
            squad_id="test",
            claw_role="content",
            blueprint_dir=str(self.bp_dir),
            versions_dir=self.versions_dir,
        )

    def test_initial_version(self):
        self.assertEqual(self.manager.current_version(), "0.1.0")

    def test_bump_version(self):
        new = self.manager.bump_version("first tool deployed")
        self.assertEqual(new, "0.1.1")
        self.assertEqual(self.manager.current_version(), "0.1.1")

    def test_multiple_bumps(self):
        self.manager.bump_version("tool 1")
        self.manager.bump_version("tool 2")
        self.assertEqual(self.manager.current_version(), "0.1.2")

    def test_export_creates_snapshot(self):
        snapshot = self.manager.export(niche_tags=["content-agency"])
        self.assertEqual(snapshot.meta.version, "0.1.0")
        self.assertIn("content-agency", snapshot.meta.niche_tags)
        self.assertIn("digest", snapshot.integrity)
        self.assertTrue(len(snapshot.integrity["digest"]) == 64)

    def test_verify_integrity(self):
        snapshot = self.manager.export()
        self.assertTrue(self.manager.verify_integrity(snapshot))

    def test_verify_integrity_detects_tampering(self):
        snapshot = self.manager.export()
        snapshot.claw_config["tampered"] = True
        self.assertFalse(self.manager.verify_integrity(snapshot))

    def test_diff_shows_tool_changes(self):
        # Export v0.1.0
        self.manager.export()
        # Add tools and bump
        self.manager.bump_version("added tool")
        # Create a registry with a tool for the second export
        reg_dir = os.path.join(self.tmp, "tools")
        registry = ToolRegistry("test", "content", registry_dir=reg_dir)
        tool = BuiltTool(
            proposal=ToolProposal(
                tool_name="style_desc",
                tool_type="classifier",
                trigger_pattern=EvolutionPattern(
                    pattern_type="classifier",
                    trigger_description="t",
                    metric_target="x",
                    confidence=0.8,
                ),
                metric_target="x",
            ),
            tool_name="style_desc",
            tool_type="classifier",
        )
        registry.register(tool)
        manager2 = BlueprintManager(
            "test",
            "content",
            str(self.bp_dir),
            tool_registry=registry,
            versions_dir=self.versions_dir,
        )
        manager2.export()
        diff = manager2.diff("0.1.0", "0.1.1")
        self.assertIn("style_desc", diff.tools_added)

    def test_rollback(self):
        self.manager.export()
        self.manager.bump_version("tool")
        self.manager.export()
        self.assertTrue(self.manager.rollback("0.1.0", reason="reverting"))
        self.assertEqual(self.manager.current_version(), "0.1.0")

    def test_list_versions(self):
        self.manager.bump_version("v1")
        self.manager.bump_version("v2")
        versions = self.manager.list_versions()
        self.assertEqual(len(versions), 2)


# ═══════════════════════════════════════════════════════════════════════
#  EvolutionCycle Tests
# ═══════════════════════════════════════════════════════════════════════


class TestEvolutionCycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bp_dir = Path(self.tmp) / "milimo-blueprint"
        (self.bp_dir / "roles").mkdir(parents=True)
        (self.bp_dir / "policies").mkdir(parents=True)

        with (self.bp_dir / "roles" / "content-claw.yaml").open("w") as f:
            f.write("role: content\n")
        with (self.bp_dir / "policies" / "content-sandbox.yaml").open("w") as f:
            f.write(
                "filesystem_policy:\n  read_write:\n    - /sandbox/content\n    - /tmp\n"
            )

        self.config = EvolutionConfig(
            minimum_actions=5,
            min_confidence=0.3,
            min_improvement_percent=3.0,
        )

        self.cycle = EvolutionCycle(
            squad_id="test",
            claw_role="content",
            blueprint_dir=str(self.bp_dir),
            log_dir=os.path.join(self.tmp, "logs"),
            registry_dir=os.path.join(self.tmp, "registry"),
            config=self.config,
        )

    def test_skips_on_insufficient_data(self):
        # Only 2 actions, need 5
        self.cycle.operation_log.record(
            ActionRecord(action_type="draft", outcome="approved")
        )
        self.cycle.operation_log.record(
            ActionRecord(action_type="draft", outcome="approved")
        )
        result = self.cycle.run()
        self.assertEqual(result.stage_reached, "observe")
        self.assertIn("Insufficient", result.skipped_reason)

    def test_full_cycle_with_edit_pattern(self):
        """Full cycle with enough data to trigger edit pattern → tool deployment."""
        for i in range(15):
            self.cycle.operation_log.record(
                ActionRecord(
                    action_type="social_post_draft",
                    outcome="edited",
                    edits={"tone": "hype → educational"},
                    metrics={"engagement": 0.04},
                )
            )
        for i in range(5):
            self.cycle.operation_log.record(
                ActionRecord(
                    action_type="social_post_draft",
                    outcome="approved",
                    metrics={"engagement": 0.05},
                )
            )
        result = self.cycle.run()
        # Should reach at least propose stage
        self.assertIn(result.stage_reached, ["propose", "build", "deploy"])

    def test_dry_run_stops_at_propose(self):
        for i in range(20):
            self.cycle.operation_log.record(
                ActionRecord(
                    action_type="post",
                    outcome="edited",
                    edits={"tone": "fix"},
                    metrics={"engagement": 0.04},
                )
            )
        result = self.cycle.run(dry_run=True)
        if result.stage_reached != "observe" and result.stage_reached != "identify":
            self.assertEqual(result.stage_reached, "propose")
            self.assertIn("Dry run", result.skipped_reason)

    def test_result_serialization(self):
        result = self.cycle.run()
        d = result.to_dict()
        self.assertIn("claw_role", d)
        self.assertIn("stage_reached", d)


class TestEvolutionScheduler(unittest.TestCase):
    def test_register_and_trigger(self):
        tmp = tempfile.mkdtemp()
        bp_dir = Path(tmp) / "bp"
        (bp_dir / "roles").mkdir(parents=True)
        (bp_dir / "policies").mkdir(parents=True)

        config = EvolutionConfig(minimum_actions=100)  # won't find enough
        cycle = EvolutionCycle(
            squad_id="test",
            claw_role="content",
            blueprint_dir=str(bp_dir),
            log_dir=os.path.join(tmp, "logs"),
            config=config,
        )

        scheduler = EvolutionScheduler()
        scheduler.register(cycle)
        results = scheduler.trigger()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].claw_role, "content")

    def test_get_status(self):
        scheduler = EvolutionScheduler()
        status = scheduler.get_status()
        self.assertEqual(status["registered_claws"], [])
        self.assertEqual(status["total_cycles_run"], 0)


class TestEvolutionConfig(unittest.TestCase):
    def test_load_from_file(self):
        config_path = Path(__file__).resolve().parent.parent / "evolution_config.yaml"
        if config_path.exists():
            config = EvolutionConfig.from_file(config_path)
            self.assertEqual(config.cycle_interval_days, 7)
            self.assertEqual(config.min_improvement_percent, 5.0)
            self.assertEqual(config.max_tools_per_claw, 30)
        else:
            # Use defaults
            config = EvolutionConfig()
            self.assertEqual(config.cycle_interval_days, 7)

    def test_defaults(self):
        config = EvolutionConfig()
        self.assertFalse(config.require_proposal_approval)
        self.assertTrue(config.notify_war_room)


if __name__ == "__main__":
    unittest.main()
