# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Pricing Engine."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
)
from finance.signal_dispatcher import FinanceSignalDispatcher
from finance.pricing_engine import PricingEngine, PricingEstimate, COMPLEXITY_TO_HOURS


class MockInferenceClient:
    """Mock inference client."""

    def __init__(self, response: str | None = None, should_fail: bool = False):
        self.response = response
        self.should_fail = should_fail
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        self.calls.append(
            {"prompt": prompt, "data_type": data_type, "max_tokens": max_tokens}
        )
        if self.should_fail:
            raise RuntimeError("Inference failed")
        if self.response:
            return self.response
        return json.dumps(
            {
                "estimated_hours": 15,
                "recommended_rate": 120,
                "scope_notes": "Test estimate",
            }
        )


class MockMeshGateway:
    """Mock mesh gateway."""

    def __init__(self):
        self.sent_messages: list[dict] = []

    def send(
        self,
        message_type: str,
        recipient_role: str,
        sender_role: str,
        payload: dict,
        message_id: str,
        timestamp: str,
    ) -> bool:
        self.sent_messages.append(
            {
                "message_type": message_type,
                "recipient_role": recipient_role,
                "sender_role": sender_role,
                "payload": payload,
                "message_id": message_id,
                "timestamp": timestamp,
            }
        )
        return True


class TestPricingEngine:
    """Tests for PricingEngine."""

    @pytest.fixture
    def fs(self, tmp_path: Path):
        fs = FinanceFilesystemInit(tmp_path)
        fs.initialize()
        return fs

    @pytest.fixture
    def operational_log(self, fs: FinanceFilesystemInit):
        return FinanceOperationalLog(fs.base / "logs" / "operational.log")

    @pytest.fixture
    def gateway(self):
        return MockMeshGateway()

    @pytest.fixture
    def dispatcher(self, gateway, operational_log):
        return FinanceSignalDispatcher(gateway, operational_log)

    @pytest.fixture
    def inference_client(self):
        return MockInferenceClient()

    @pytest.fixture
    def pricing_engine(self, fs, inference_client, dispatcher, operational_log):
        return PricingEngine(
            fs=fs,
            inference_client=inference_client,
            dispatcher=dispatcher,
            operational_log=operational_log,
        )

    def test_handle_pricing_query_returns_estimate(self, pricing_engine):
        """handle_pricing_query returns a PricingEstimate."""
        message = {
            "project_id": "proj-123",
            "scope_description": "Build a landing page",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }

        estimate = pricing_engine.handle_pricing_query(message)

        assert isinstance(estimate, PricingEstimate)
        assert estimate.project_id == "proj-123"
        assert estimate.complexity_estimate == "medium"
        assert estimate.deadline == "2026-04-01"

    def test_pricing_query_writes_estimate_file(self, pricing_engine, fs):
        """Pricing estimate is written to correct path."""
        message = {
            "project_id": "proj-456",
            "scope_description": "API integration",
            "complexity_estimate": "high",
            "deadline": "2026-05-01",
        }

        pricing_engine.handle_pricing_query(message)

        estimate_path = fs.get_pricing_estimate_path("proj-456")
        assert estimate_path.exists()

        data = json.loads(estimate_path.read_text())
        assert data["project_id"] == "proj-456"

    def test_pricing_query_sends_pricing_response(self, pricing_engine, gateway):
        """Pricing response is sent via dispatcher."""
        message = {
            "project_id": "proj-789",
            "scope_description": "Database migration",
            "complexity_estimate": "low",
            "deadline": "2026-03-25",
        }

        pricing_engine.handle_pricing_query(message)

        assert len(gateway.sent_messages) == 1
        msg = gateway.sent_messages[0]
        assert msg["message_type"] == "pricing_response"
        assert msg["payload"]["project_id"] == "proj-789"

    def test_inference_call_includes_data_type(self, pricing_engine, inference_client):
        """Inference call includes data_type='scope_cost_estimation'."""
        message = {
            "project_id": "proj-111",
            "scope_description": "Test project",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }

        pricing_engine.handle_pricing_query(message)

        assert len(inference_client.calls) == 1
        assert inference_client.calls[0]["data_type"] == "scope_cost_estimation"

    def test_fallback_on_inference_failure(self, pricing_engine, fs, gateway):
        """Rule-based fallback when inference fails."""
        failing_client = MockInferenceClient(should_fail=True)
        pricing_engine.inference_client = failing_client

        message = {
            "project_id": "proj-222",
            "scope_description": "Fallback test",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }

        estimate = pricing_engine.handle_pricing_query(message)

        assert estimate.data_quality == "estimated"
        assert estimate.project_id == "proj-222"

        assert len(gateway.sent_messages) == 1

    def test_load_pricing_rules_returns_defaults(self, pricing_engine):
        """load_pricing_rules returns defaults when file missing."""
        rules = pricing_engine.load_pricing_rules()

        assert "default_hourly_rate" in rules
        assert "floor_multiplier" in rules
        assert "ceiling_multiplier" in rules

    def test_load_pricing_rules_reads_file(self, pricing_engine, fs):
        """load_pricing_rules reads from rules.json."""
        rules_path = fs.base / "pricing" / "rules.json"
        custom_rules = {
            "default_hourly_rate": 150,
            "floor_multiplier": 0.75,
            "ceiling_multiplier": 1.75,
        }
        rules_path.write_text(json.dumps(custom_rules))

        rules = pricing_engine.load_pricing_rules()

        assert rules["default_hourly_rate"] == 150
        assert rules["floor_multiplier"] == 0.75

    def test_load_historical_calibration_returns_empty_when_no_history(
        self, pricing_engine
    ):
        """load_historical_calibration returns empty when no history."""
        historical = pricing_engine.load_historical_calibration("medium")

        assert historical == []

    def test_load_historical_calibration_reads_files(self, pricing_engine, fs):
        """load_historical_calibration reads matching history files."""
        history_dir = fs.base / "pricing" / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        history_data = {
            "complexity_estimate": "medium",
            "estimated_hours": 20,
            "actual_hours": 22,
            "accuracy_pct": 90,
        }
        (history_dir / "proj-old1.json").write_text(json.dumps(history_data))

        historical = pricing_engine.load_historical_calibration("medium")

        assert len(historical) == 1
        assert historical[0]["estimated_hours"] == 20

    def test_complexity_to_hours_mapping(self):
        """Complexity maps to expected hours."""
        assert COMPLEXITY_TO_HOURS["low"] == 8
        assert COMPLEXITY_TO_HOURS["medium"] == 20
        assert COMPLEXITY_TO_HOURS["high"] == 40
        assert COMPLEXITY_TO_HOURS["complex"] == 80

    def test_rule_based_fallback_uses_complexity(self, pricing_engine):
        """Rule-based fallback uses complexity for hours."""
        rules = {"default_hourly_rate": 100}

        estimate = pricing_engine._rule_based_fallback("Test scope", "high", rules)

        assert estimate.estimated_hours == COMPLEXITY_TO_HOURS["high"]
        assert estimate.data_quality == "estimated"

    def test_floor_price_calculation(self, pricing_engine):
        """Floor price uses floor_multiplier."""
        message = {
            "project_id": "proj-floor",
            "scope_description": "Test",
            "complexity_estimate": "low",
            "deadline": "2026-04-01",
        }

        estimate = pricing_engine.handle_pricing_query(message)

        expected_floor = estimate.estimated_hours * estimate.recommended_rate * 0.8
        assert abs(estimate.floor_price - expected_floor) < 1

    def test_ceiling_price_calculation(self, pricing_engine):
        """Ceiling price uses ceiling_multiplier."""
        message = {
            "project_id": "proj-ceiling",
            "scope_description": "Test",
            "complexity_estimate": "low",
            "deadline": "2026-04-01",
        }

        estimate = pricing_engine.handle_pricing_query(message)

        expected_ceiling = estimate.estimated_hours * estimate.recommended_rate * 1.5
        assert abs(estimate.ceiling_price - expected_ceiling) < 1

    def test_update_actual_cost_writes_history(self, pricing_engine, fs):
        """update_actual_cost writes to history path."""
        message = {
            "project_id": "proj-actual",
            "scope_description": "Test",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }
        pricing_engine.handle_pricing_query(message)

        pricing_engine.update_actual_cost(
            "proj-actual", actual_hours=25, actual_cost=2500
        )

        history_path = fs.get_pricing_history_path("proj-actual")
        assert history_path.exists()

        data = json.loads(history_path.read_text())
        assert data["actual_hours"] == 25
        assert data["actual_cost"] == 2500
        assert "accuracy_pct" in data

    def test_accuracy_calculation(self, pricing_engine, fs):
        """Accuracy is calculated correctly."""
        message = {
            "project_id": "proj-accuracy",
            "scope_description": "Test",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }
        estimate = pricing_engine.handle_pricing_query(message)

        pricing_engine.update_actual_cost(
            "proj-accuracy", actual_hours=22, actual_cost=2200
        )

        history_path = fs.get_pricing_history_path("proj-accuracy")
        data = json.loads(history_path.read_text())

        expected_accuracy = 100 - abs(
            (22 - estimate.estimated_hours) / estimate.estimated_hours * 100
        )
        assert abs(data["accuracy_pct"] - expected_accuracy) < 1

    def test_logged_to_operational_log(self, pricing_engine, operational_log):
        """Pricing query is logged to operational.log."""
        message = {
            "project_id": "proj-logged",
            "scope_description": "Test",
            "complexity_estimate": "medium",
            "deadline": "2026-04-01",
        }

        pricing_engine.handle_pricing_query(message)

        entries = operational_log.read_recent(days=1)
        assert any(e.action_type == "pricing_query_answered" for e in entries)

    def test_data_quality_complete_with_history(self, pricing_engine, fs):
        """data_quality is 'complete' when history exists."""
        history_dir = fs.base / "pricing" / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / "old-proj.json").write_text(
            json.dumps(
                {
                    "complexity_estimate": "low",
                    "estimated_hours": 8,
                    "actual_hours": 9,
                    "accuracy_pct": 88,
                }
            )
        )

        message = {
            "project_id": "proj-quality",
            "scope_description": "Test",
            "complexity_estimate": "low",
            "deadline": "2026-04-01",
        }

        estimate = pricing_engine.handle_pricing_query(message)

        assert estimate.data_quality == "complete"
        assert estimate.history_projects_used >= 1
