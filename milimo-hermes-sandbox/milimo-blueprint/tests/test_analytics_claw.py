# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for Analytics Claw main entry point.
"""

import shutil
import tempfile
from datetime import datetime, timezone
from collections.abc import Iterator
from pathlib import Path

import pytest

from orchestrator.analytics.analytics_claw import AnalyticsClaw


@pytest.fixture
def temp_sandbox() -> Iterator[Path]:
    sandbox = Path(tempfile.mkdtemp(prefix="claw_test_"))
    yield sandbox
    shutil.rmtree(sandbox, ignore_errors=True)


class MockInferenceClient:
    def complete(self, prompt: str, data_type: str, max_tokens: int = 500) -> str:
        return "Test inference response."


class TestAnalyticsClaw:
    def test_init_creates_instance(self, temp_sandbox: Path):
        claw = AnalyticsClaw(
            squad_id="test-squad",
            inference_client=MockInferenceClient(),
            base_path=temp_sandbox,
        )
        assert claw.squad_id == "test-squad"

    def test_startup_initializes_filesystem(self, temp_sandbox: Path):
        claw = AnalyticsClaw(
            squad_id="test-squad",
            base_path=temp_sandbox,
        )
        claw.startup()
        assert claw._started
        assert claw.fs is not None
        claw.shutdown()

    def test_startup_creates_required_directories(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        for dirname in ["reports", "signals", "data", "baselines", "logs"]:
            dir_path = temp_sandbox / dirname
            assert dir_path.exists(), f"Directory {dirname} not created"

        claw.shutdown()

    def test_startup_initializes_components(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        assert claw.signal_processor is not None
        assert claw.query_handler is not None
        assert claw.baseline_manager is not None
        assert claw.anomaly_detector is not None
        assert claw.report_generator is not None
        assert claw.opportunity_scorer is not None
        assert claw.forward_projector is not None
        assert claw.scheduler is not None

        claw.shutdown()

    def test_shutdown_stops_scheduler(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()
        claw.shutdown()

        assert not claw._started
        assert claw.scheduler is not None
        assert not claw.scheduler._running

    def test_handle_inbound_routes_messages(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        message = {
            "message_id": "test-001",
            "message_type": "performance_signal",
            "sender_role": "content",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "post_id": "post-001",
                "platform": "linkedin",
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.08},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        }

        claw.handle_inbound(message)

        claw.shutdown()

    def test_handle_inbound_unknown_message_type(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        message = {
            "message_id": "test-002",
            "message_type": "unknown_type",
            "sender_role": "test",
        }

        claw.handle_inbound(message)

        claw.shutdown()

    def test_handle_inbound_never_crashes_on_bad_input(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        bad_messages = [
            {},
            {"message_type": "test"},
            {"message_id": "test", "message_type": None},
            {"message_id": "test", "message_type": "test", "payload": "not a dict"},
        ]

        for msg in bad_messages:
            try:
                claw.handle_inbound(msg)
            except Exception as e:
                pytest.fail(f"handle_inbound raised exception: {e}")

        claw.shutdown()

    def test_startup_logs_to_operational_log(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        log_path = temp_sandbox / "logs" / "operational.log"
        assert log_path.exists()

        content = log_path.read_text()
        assert "claw_started" in content

        claw.shutdown()

    def test_shutdown_logs_to_operational_log(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()
        claw.shutdown()

        log_path = temp_sandbox / "logs" / "operational.log"
        content = log_path.read_text()
        assert "claw_stopped" in content

    def test_double_startup_safe(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()
        claw.startup()

        assert claw._started

        claw.shutdown()

    def test_double_shutdown_safe(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()
        claw.shutdown()
        claw.shutdown()

        assert not claw._started

    def test_inference_client_passed_to_components(self, temp_sandbox: Path):
        inference_client = MockInferenceClient()
        claw = AnalyticsClaw(
            base_path=temp_sandbox,
            inference_client=inference_client,
        )
        claw.startup()

        rg = claw.report_generator
        assert rg is not None
        assert rg.inference_client is inference_client

        claw.shutdown()

    def test_handle_performance_signal_creates_data(self, temp_sandbox: Path):
        claw = AnalyticsClaw(base_path=temp_sandbox)
        claw.startup()

        message = {
            "message_id": "perf-001",
            "message_type": "performance_signal",
            "sender_role": "content",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "post_id": "post-001",
                "platform": "linkedin",
                "content_type": "article",
                "engagement_data": {"engagement_rate": 0.08},
                "publish_time": datetime.now(timezone.utc).isoformat(),
            },
        }

        claw.handle_inbound(message)

        data_dir = temp_sandbox / "data" / "content-performance"
        assert data_dir.exists()

        claw.shutdown()

    def test_handle_client_health_signal_low_score(self, temp_sandbox: Path):
        dispatched = []

        def mock_sender(msg):
            dispatched.append(msg)

        claw = AnalyticsClaw(
            base_path=temp_sandbox,
            mesh_sender=mock_sender,
        )
        claw.startup()

        message = {
            "message_id": "health-001",
            "message_type": "client_health_signal",
            "sender_role": "ops",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "client_id": "client-001",
                "health_score": 5.0,
                "health_factors": ["risk"],
            },
        }

        claw.handle_inbound(message)

        health_path = temp_sandbox / "data" / "client-health" / "client-001"
        assert health_path.exists()

        claw.shutdown()
