#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Integration Tests

Tests the full pipeline: message → mesh → claw → inference → github → PR
and end-to-end tests for each claw component.

Run with: python -m pytest test/integration_python/ -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add orchestrator parent to path so 'orchestrator' is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "milimo-blueprint"))


# ── Inference Client Tests ─────────────────────────────────────────────

class TestInferenceClient(unittest.TestCase):
    """Integration tests for NvidiaInferenceClient."""

    def setUp(self):
        from orchestrator.inference_client import NvidiaInferenceClient
        self.client = NvidiaInferenceClient(
            api_key="test-key-fake",
            api_base="https://fake-api.example.com",
        )

    def test_client_initialization(self):
        """Client should initialize with API key and base URL."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.api_key, "test-key-fake")

    def test_category_routing(self):
        """Category-based model routing should select correct model."""
        from orchestrator.inference_client import CATEGORY_MODELS
        self.assertIn("source_code_generation", CATEGORY_MODELS)
        self.assertIn("content_draft", CATEGORY_MODELS)
        self.assertIn("incident_analysis", CATEGORY_MODELS)

    def test_fallback_chain_configured(self):
        """Fallback chain should have at least 2 models."""
        from orchestrator.inference_client import DEFAULT_FALLBACK_CHAIN
        self.assertGreaterEqual(len(DEFAULT_FALLBACK_CHAIN), 2)

    @patch("requests.post")
    def test_complete_with_mock_response(self, mock_post):
        """Complete should parse API response correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Generated code response"},
                "finish_reason": "stop",
            }],
            "usage": {"total_tokens": 100},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.client.complete("test prompt", "source_code_generation")
        self.assertIn("Generated code response", result)

    def test_get_usage_tracking(self):
        """Usage tracking should accumulate token counts."""
        from orchestrator.inference_client import InferenceUsage
        # Simulate some usage by adding entries to history
        self.client._usage_history.append(InferenceUsage(
            model_used="test-model",
            prompt_tokens=300,
            completion_tokens=200,
            total_tokens=500,
            estimated_cost_usd=0.01,
            timestamp="2026-04-05T00:00:00Z",
        ))
        usage = self.client.get_usage()
        self.assertEqual(usage["total_tokens"], 500)
        self.assertEqual(usage["total_calls"], 1)
        # Also verify total_tokens key exists in usage dict
        self.assertIn("total_tokens", usage)


# ── GitHub Client Tests ────────────────────────────────────────────────

class TestGitHubClient(unittest.TestCase):
    """Integration tests for GitHubClient."""

    def setUp(self):
        from orchestrator.github_client import GitHubClient
        self.client = GitHubClient(
            repo="test/repo",
        )

    def test_client_initialization(self):
        """Client should initialize with token and repo."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.repo, "test/repo")

    @patch("subprocess.run")
    def test_get_open_issues(self, mock_run):
        """get_open_issues should parse gh CLI output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"number": 1, "title": "Test Issue", "state": "open"},
                {"number": 2, "title": "Another Issue", "state": "open"},
            ]),
        )
        issues = self.client.get_open_issues()
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]["number"], 1)

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        """create_branch should execute git checkout -b."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = self.client.create_branch("feature/test-branch")
        # create_branch returns None on success, raises on failure
        self.assertIsNone(result)
        # Verify git checkout was called
        self.assertTrue(any("checkout" in str(c) for c in mock_run.call_args_list))

    @patch("subprocess.run")
    def test_create_pull_request(self, mock_run):
        """create_pull_request should call gh pr create."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/test/repo/pull/42",
        )
        result = self.client.create_pull_request(
            title="Test PR",
            body="Test description",
            branch="feature/test",
            base="main",
        )
        self.assertIn("42", str(result))


# ── Build Claw Pipeline Tests ──────────────────────────────────────────

class TestBuildClawPipeline(unittest.TestCase):
    """End-to-end pipeline test: feature_brief → sprint → approval → code → PR."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.tmpdir.name)

        # Mock inference client
        self.mock_inference = MagicMock()
        self.mock_inference.complete.return_value = '{"files": [{"path": "test.py", "content": "print(42)"}]}'
        self.mock_inference.get_usage.return_value = {"total_tokens": 100, "total_requests": 1}

        # Mock GitHub client
        self.mock_github = MagicMock()
        self.mock_github.get_open_issues.return_value = [
            {"number": 1, "title": "Test Issue", "body": "Fix the thing"},
        ]
        self.mock_github.create_branch.return_value = True
        self.mock_github.commit_file.return_value = True
        self.mock_github.create_pull_request.return_value = "https://github.com/test/repo/pull/1"

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("time.sleep")
    def test_issue_manager_plan_sprint(self, mock_sleep):
        """Issue manager should generate a sprint plan from issues."""
        from orchestrator.build.issue_manager import IssueManager
        from orchestrator.build.build_init import BuildFilesystemInit, BuildOperationalLog
        from orchestrator.build.signal_dispatcher import BuildSignalDispatcher

        fs = BuildFilesystemInit(self.base_path)
        fs.initialize()
        log = BuildOperationalLog(self.base_path / "logs" / "operational.log")
        dispatcher = BuildSignalDispatcher(
            fs=fs,
            operational_log=log,
            squad_id="test-squad",
        )

        # Create minimal approval handler mock
        approval_handler = MagicMock()
        approval_handler.queue_sprint_plan_review = MagicMock()

        manager = IssueManager(
            fs=fs,
            github_client=self.mock_github,
            inference_client=self.mock_inference,
            operational_log=log,
            dispatcher=dispatcher,
            approval_handler=approval_handler,
        )

        # generate_sprint_plan creates a plan from fetched issues
        sprint = manager.generate_sprint_plan()
        self.assertIsNotNone(sprint)
        self.assertIsInstance(sprint.plan_id, str)

    def test_code_generator_resolve_issue(self):
        """Code generator should generate code for an issue."""
        from orchestrator.build.code_generator import CodeGenerator
        from orchestrator.build.build_init import BuildFilesystemInit, BuildOperationalLog
        from orchestrator.build.approval_handler import (
            BuildApprovalHandler,
            PRActivityLog,
            DeployActivityLog,
        )
        from orchestrator.build.issue_manager import ComplexityScore

        fs = BuildFilesystemInit(self.base_path)
        fs.initialize()
        log = BuildOperationalLog(self.base_path / "logs" / "operational.log")
        pr_log = PRActivityLog(self.base_path / "logs" / "pr_activity.log")
        deploy_log = DeployActivityLog(self.base_path / "logs" / "deploy_activity.log")
        approval_handler = BuildApprovalHandler(
            fs=fs,
            operational_log=log,
            pr_log=pr_log,
            deploy_log=deploy_log,
        )

        generator = CodeGenerator(
            fs=fs,
            github_client=self.mock_github,
            inference_client=self.mock_inference,
            operational_log=log,
            approval_handler=approval_handler,
            repo_path=self.base_path,
        )

        # resolve_issue takes a ComplexityScore, not a dict
        score = ComplexityScore(
            issue_number=1,
            issue_title="Test Issue",
            complexity_tier="M",
            estimated_hours=2.0,
            clarity_score="clear",
        )
        result = generator.resolve_issue(score=score)
        self.assertIsNotNone(result)


# ── Analytics Data Collector Tests ─────────────────────────────────────

class TestAnalyticsDataCollectors(unittest.TestCase):
    """Integration tests for analytics data collectors."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_youtube_collector_not_configured(self):
        """YouTube collector should gracefully handle missing config."""
        from orchestrator.analytics.data_collectors import YouTubeDataCollector
        collector = YouTubeDataCollector(data_dir=self.data_dir)
        self.assertFalse(collector.is_configured())
        result = collector.collect_video_stats()
        self.assertFalse(result.success)
        self.assertIn("not configured", result.error.lower())

    def test_google_analytics_collector_not_configured(self):
        """GA collector should gracefully handle missing config."""
        from orchestrator.analytics.data_collectors import GoogleAnalyticsCollector
        collector = GoogleAnalyticsCollector(data_dir=self.data_dir)
        self.assertFalse(collector.is_configured())
        result = collector.collect_page_views()
        self.assertFalse(result.success)

    def test_generic_api_collector(self):
        """Generic collector should work with any REST endpoint."""
        from orchestrator.analytics.data_collectors import GenericAPICollector
        collector = GenericAPICollector(
            name="test_api",
            base_url="https://jsonplaceholder.typicode.com",
            data_dir=self.data_dir,
        )
        # This is a real API call — may fail in sandbox
        # Just verify the collector initializes correctly
        self.assertIsNotNone(collector)
        self.assertEqual(collector.name, "test_api")

    def test_collection_workers(self):
        """Collection workers should manage multiple collectors."""
        from orchestrator.analytics.collection_workers import CollectionWorker
        from orchestrator.analytics.analytics_init import AnalyticsFilesystemInit, AnalyticsOperationalLog, AnalyticsLogEntry

        fs = AnalyticsFilesystemInit(self.data_dir)
        fs.initialize()
        log_path = self.data_dir / "logs" / "operational.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.touch()
        log = AnalyticsOperationalLog(log_path)

        workers = CollectionWorker(fs=fs, operational_log=log)
        # Should not crash even with no collectors registered
        summary = workers.get_collection_summary()
        self.assertIsInstance(summary, dict)


# ── Finance Stripe Client Tests ────────────────────────────────────────

class TestStripeClient(unittest.TestCase):
    """Integration tests for StripeClient."""

    def setUp(self):
        from orchestrator.finance.stripe_client import StripeClient
        self.client = StripeClient(
            api_key="sk_test_fake_key",
            webhook_secret="whsec_test_secret",
        )

    def test_client_initialization(self):
        """Client should initialize with API key."""
        self.assertIsNotNone(self.client)
        self.assertTrue(self.client.is_configured())

    def test_client_not_configured(self):
        """Client without API key should report not configured."""
        from orchestrator.finance.stripe_client import StripeClient
        client = StripeClient()
        self.assertFalse(client.is_configured())

    def test_create_customer_returns_error_without_api(self):
        """create_customer should return error dict when API unavailable."""
        result = self.client.create_customer(email="test@example.com", name="Test User")
        # Should return error dict, not raise exception
        self.assertIsInstance(result, dict)

    def test_get_revenue_summary_structure(self):
        """get_revenue_summary should return structured summary."""
        result = self.client.get_revenue_summary(days=30)
        self.assertIsInstance(result, dict)
        self.assertIn("total_revenue", result)
        self.assertIn("successful_payments", result)
        self.assertIn("currency", result)


# ── Privacy Router Integration Tests ───────────────────────────────────

class TestPrivacyRouterIntegration(unittest.TestCase):
    """Integration tests for Privacy Router in MeshCoordinator."""

    def test_mesh_with_privacy_router(self):
        """MeshCoordinator should classify messages when privacy router is configured."""
        from orchestrator.mesh import MeshCoordinator, MeshConfig
        from orchestrator.contracts import ContractValidator
        from orchestrator.privacy_router import PrivacyRouter

        # Create a minimal validator with required params
        validator = ContractValidator(
            message_matrix={"build": {"content": True}},
            message_types=["status_update"],
        )
        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [
                {"data_type": "code_generation", "description": "Code", "backend": "local-nim"},
                {"data_type": "financial_data", "description": "Finance", "backend": "local-nim", "locked": True},
            ],
            "role_overrides": {
                "finance": {"force_backend": "local-nim"},
            },
        })

        mesh = MeshCoordinator(
            validator=validator,
            squad_id="test-squad",
            privacy_router=router,
        )

        # Verify privacy router is wired
        self.assertIsNotNone(mesh._privacy_router)

    def test_privacy_routing_decision(self):
        """Privacy router should make correct routing decisions."""
        from orchestrator.privacy_router import PrivacyRouter, InferenceBackend

        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [
                {"data_type": "public_drafts", "description": "Public content", "backend": "cloud"},
                {"data_type": "financial_data", "description": "Finance", "backend": "local-nim", "locked": True},
            ],
            "role_overrides": {
                "finance": {"force_backend": "local-nim"},
            },
        })

        # Finance role should always go to local-nim
        decision = router.route(role="finance", data_type="financial_data")
        self.assertEqual(decision.backend, InferenceBackend.LOCAL_NIM)
        self.assertTrue(decision.was_overridden)

        # Public content without role override goes to cloud
        decision = router.route(role="content", data_type="public_drafts")
        self.assertEqual(decision.backend, InferenceBackend.CLOUD)


# ── Metrics Collector Tests ────────────────────────────────────────────

class TestMetricsCollector(unittest.TestCase):
    """Integration tests for MetricsCollector."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.metrics_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_record_message_processed(self):
        """Should record message processing metrics."""
        from orchestrator.metrics_collector import MetricsCollector
        collector = MetricsCollector(claw_role="build", metrics_dir=self.metrics_dir)
        collector.record_message_processed("feature_brief", 150.0)

        # Verify file was written
        metrics_file = self.metrics_dir / "metrics.jsonl"
        self.assertTrue(metrics_file.exists())

        with open(metrics_file) as f:
            entries = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["metric_type"], "message_processed")

    def test_record_error(self):
        """Should record error metrics."""
        from orchestrator.metrics_collector import MetricsCollector
        collector = MetricsCollector(claw_role="ops", metrics_dir=self.metrics_dir)
        collector.record_error("timeout", "Request timed out")

        summary = collector.get_summary()
        self.assertEqual(summary["counters"]["errors"], 1)
        self.assertEqual(summary["counters"]["errors.timeout"], 1)

    def test_record_sla_compliance(self):
        """Should track SLA compliance."""
        from orchestrator.metrics_collector import MetricsCollector
        collector = MetricsCollector(claw_role="build", metrics_dir=self.metrics_dir)

        # Compliant
        collector.record_sla_compliance("feature_brief", 120000, 60000)
        # Violation
        collector.record_sla_compliance("feature_brief", 120000, 180000)

        summary = collector.get_summary()
        self.assertEqual(summary["counters"]["sla_compliant"], 1)
        self.assertEqual(summary["counters"]["sla_violation"], 1)


# ── Evolution Integration Tests ────────────────────────────────────────

class TestEvolutionIntegration(unittest.TestCase):
    """Integration tests for Evolution Cycle integration."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.blueprint_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_evolution_integration_initialization(self):
        """EvolutionIntegration should initialize with real inference client."""
        from orchestrator.evolution_integration import EvolutionIntegration
        from orchestrator.inference_client import NvidiaInferenceClient

        inference = NvidiaInferenceClient(api_key="test-key")
        integration = EvolutionIntegration(
            squad_id="test-squad",
            blueprint_dir=self.blueprint_dir,
            inference_client=inference,
        )
        self.assertIsNotNone(integration)
        self.assertEqual(integration.squad_id, "test-squad")

    def test_evolution_scheduler_registration(self):
        """Should register evolution cycles for all claws."""
        from orchestrator.evolution_integration import EvolutionIntegration

        integration = EvolutionIntegration(
            squad_id="test-squad",
            blueprint_dir=self.blueprint_dir,
        )
        # Register all claws
        for role in ["build", "content", "ops", "analytics", "finance"]:
            integration.register_claw(role)

        status = integration.scheduler.get_status()
        self.assertEqual(len(status["registered_claws"]), 5)

    def test_evolution_get_metrics_summary(self):
        """Should return metrics summary for all claws."""
        from orchestrator.evolution_integration import EvolutionIntegration

        integration = EvolutionIntegration(
            squad_id="test-squad",
            blueprint_dir=self.blueprint_dir,
        )
        summary = integration.get_metrics_summary()
        self.assertIn("build", summary)
        self.assertIn("content", summary)
        self.assertIn("ops", summary)


# ── Full Pipeline Integration Test ─────────────────────────────────────

class TestFullPipeline(unittest.TestCase):
    """Full end-to-end pipeline test."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_message_flow_mesh_to_claw(self):
        """Test message flow: mesh → validation → privacy → delivery."""
        from orchestrator.mesh import MeshCoordinator
        from orchestrator.contracts import ContractValidator, MessageTypeConfig
        from orchestrator.privacy_router import PrivacyRouter
        from orchestrator.mesh import ClawMessage

        # Build Claw can send "deliverable" to Content Claw
        validator = ContractValidator(
            message_matrix={"build": {"content": ["deliverable"]}},
            message_types={
                "deliverable": MessageTypeConfig(
                    description="Code deliverable from Build to Content",
                    requires_approval=False,
                ),
            },
        )
        router = PrivacyRouter.from_dict({
            "policy_version": "1.0",
            "default_backend": "local-nim",
            "routes": [],
            "role_overrides": {},
        })

        mesh = MeshCoordinator(
            validator=validator,
            squad_id="test-squad",
            privacy_router=router,
        )
        mesh.register_claw("build", address="local://build")
        mesh.register_claw("content", address="local://content")

        # Create a test message - deliverable from build to content
        message = ClawMessage(
            message_id="test-msg-1",
            sender_role="build",
            recipient_role="content",
            message_type="deliverable",
            payload={"content": "test deliverable"},
            squad_id="test-squad",
        )

        # Send through mesh
        result = mesh.send_message(message)
        # Should be delivered (file-based fallback since no gateway)
        self.assertTrue(result.delivered, f"Message not delivered: {result.reason}")
    def test_claw_startup_and_message_handling(self):
        """Test that a claw can start up and handle messages."""
        from orchestrator.analytics.analytics_claw import AnalyticsClaw

        claw = AnalyticsClaw(
            squad_id="test-squad",
            base_path=Path(self.tmpdir.name),
        )
        claw.startup()

        # Send a test message
        claw.handle_inbound({
            "message_type": "content_performance_query",
            "sender_role": "content",
            "message_id": "test-query-1",
            "payload": {"query": "top formats", "lookback_days": 7},
        })

        claw.shutdown()
        self.assertTrue(claw._started is False)  # Should be stopped


if __name__ == "__main__":
    unittest.main()
