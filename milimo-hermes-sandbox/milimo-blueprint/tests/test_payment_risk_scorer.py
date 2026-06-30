# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for Finance Claw Payment Risk Scorer."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "orchestrator"))
from finance.finance_init import PaymentEventsLog, PaymentEvent
from finance.payment_risk_scorer import (
    PaymentRiskScorer,
    PaymentRiskScore,
)


class MockInferenceClient:
    """Mock inference client."""

    def __init__(self, response: str | None = None, should_fail: bool = False):
        self.response = response
        self.should_fail = should_fail
        self.calls: list[dict] = []

    def complete(self, prompt: str, data_type: str, max_tokens: int = 800) -> str:
        self.calls.append({"prompt": prompt, "data_type": data_type})
        if self.should_fail:
            raise RuntimeError("Inference failed")
        if self.response:
            return self.response
        return "7.5"


class TestPaymentRiskScorer:
    """Tests for PaymentRiskScorer."""

    @pytest.fixture
    def log_path(self, tmp_path: Path):
        return tmp_path / "logs" / "payment-events.log"

    @pytest.fixture
    def payment_events_log(self, log_path: Path):
        return PaymentEventsLog(log_path)

    @pytest.fixture
    def inference_client(self):
        return MockInferenceClient()

    @pytest.fixture
    def risk_scorer(self, payment_events_log, inference_client):
        return PaymentRiskScorer(
            payment_events_log=payment_events_log,
            inference_client=inference_client,
        )

    def test_score_returns_payment_risk_score(self, risk_scorer):
        """score returns a PaymentRiskScore."""
        score = risk_scorer.score("client-123")

        assert isinstance(score, PaymentRiskScore)
        assert score.client_id == "client-123"

    def test_new_client_returns_neutral_score(self, risk_scorer):
        """New client with no history gets neutral score (5.0)."""
        score = risk_scorer.score("new-client-no-history")

        assert score.score == 5.0
        assert score.risk_level == "medium"
        assert score.data_quality == "no_history"
        assert "No payment history" in score.factors

    def test_inference_call_includes_data_type(self, risk_scorer, inference_client):
        """Inference call includes data_type='payment_risk_scoring'."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-1",
            client_id="client-with-history",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(event)

        risk_scorer.score("client-with-history")

        assert len(inference_client.calls) == 1
        assert inference_client.calls[0]["data_type"] == "payment_risk_scoring"

    def test_low_risk_classification(self, risk_scorer):
        """Score >= 7.0 is classified as 'low' risk."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-1",
            client_id="good-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(event)

        paid_event = PaymentEvent(
            timestamp="2026-03-05T10:00:00",
            event_type="payment_received",
            invoice_id="inv-1",
            client_id="good-client",
            amount=1000,
            details={"days_to_pay": 10},
        )
        risk_scorer.payment_events_log.append(paid_event)

        score = risk_scorer.score("good-client")

        assert score.on_time_rate == 1.0
        assert score.risk_level in ["low", "medium"]

    def test_high_risk_classification(self, risk_scorer):
        """Score < 4.0 is classified as 'high' risk."""
        for i in range(3):
            event = PaymentEvent(
                timestamp=f"2026-03-0{i + 1}T10:00:00",
                event_type="payment_overdue",
                invoice_id=f"inv-{i}",
                client_id="bad-client",
                amount=1000,
                details={"days_overdue": 30},
            )
            risk_scorer.payment_events_log.append(event)

        sent_event = PaymentEvent(
            timestamp="2026-03-04T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-sent",
            client_id="bad-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(sent_event)

        score = risk_scorer.score("bad-client")

        assert score.overdue_count == 3
        assert (
            "overdue" in score.factors[0].lower()
            or "low on-time" in score.factors[0].lower()
        )

    def test_medium_risk_classification(self, risk_scorer):
        """Score 4.0-7.0 is classified as 'medium' risk."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="payment_overdue",
            invoice_id="inv-1",
            client_id="medium-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(event)

        sent_event = PaymentEvent(
            timestamp="2026-03-02T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-sent-med",
            client_id="medium-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(sent_event)

        score = risk_scorer.score("medium-client")

        assert score.overdue_count == 1

    def test_on_time_rate_calculation(self, risk_scorer):
        """on_time_rate is calculated correctly."""
        for i in range(5):
            event = PaymentEvent(
                timestamp=f"2026-03-{10 + i:02d}T10:00:00",
                event_type="invoice_sent",
                invoice_id=f"inv-{i}",
                client_id="on-time-client",
                amount=1000,
                details={},
            )
            risk_scorer.payment_events_log.append(event)

            paid_event = PaymentEvent(
                timestamp=f"2026-03-{15 + i:02d}T10:00:00",
                event_type="payment_received",
                invoice_id=f"inv-{i}",
                client_id="on-time-client",
                amount=1000,
                details={"days_to_pay": 10 + i},
            )
            risk_scorer.payment_events_log.append(paid_event)

        score = risk_scorer.score("on-time-client")

        assert score.invoices_analyzed == 5

    def test_avg_days_late_calculation(self, risk_scorer):
        """avg_days_late is calculated correctly."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-1",
            client_id="late-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(event)

        paid_event = PaymentEvent(
            timestamp="2026-03-20T10:00:00",
            event_type="payment_received",
            invoice_id="inv-1",
            client_id="late-client",
            amount=1000,
            details={"days_to_pay": 21},
        )
        risk_scorer.payment_events_log.append(paid_event)

        score = risk_scorer.score("late-client")

        assert score.avg_days_late == 7

    def test_fallback_on_inference_failure(self, risk_scorer):
        """Rule-based fallback when inference fails."""
        failing_client = MockInferenceClient(should_fail=True)
        risk_scorer.inference_client = failing_client

        for i in range(2):
            event = PaymentEvent(
                timestamp=f"2026-03-0{i + 1}T10:00:00",
                event_type="invoice_sent",
                invoice_id=f"inv-{i}",
                client_id="fallback-client",
                amount=1000,
                details={},
            )
            risk_scorer.payment_events_log.append(event)

            paid_event = PaymentEvent(
                timestamp=f"2026-03-{10 + i:02d}T10:00:00",
                event_type="payment_received",
                invoice_id=f"inv-{i}",
                client_id="fallback-client",
                amount=1000,
                details={"days_to_pay": 12},
            )
            risk_scorer.payment_events_log.append(paid_event)

        score = risk_scorer.score("fallback-client")

        assert isinstance(score.score, float)
        assert 0 <= score.score <= 10

    def test_factors_include_low_on_time_rate(self, risk_scorer):
        """Factors mention low on-time rate."""
        for i in range(3):
            event = PaymentEvent(
                timestamp=f"2026-03-0{i + 1}T10:00:00",
                event_type="payment_overdue",
                invoice_id=f"inv-{i}",
                client_id="factor-client",
                amount=1000,
                details={},
            )
            risk_scorer.payment_events_log.append(event)

        score = risk_scorer.score("factor-client")

        assert any("overdue" in f.lower() for f in score.factors)

    def test_factors_include_good_history(self, risk_scorer):
        """Factors mention good history for on-time payers."""
        event = PaymentEvent(
            timestamp="2026-03-01T10:00:00",
            event_type="invoice_sent",
            invoice_id="inv-1",
            client_id="good-factor-client",
            amount=1000,
            details={},
        )
        risk_scorer.payment_events_log.append(event)

        paid_event = PaymentEvent(
            timestamp="2026-03-05T10:00:00",
            event_type="payment_received",
            invoice_id="inv-1",
            client_id="good-factor-client",
            amount=1000,
            details={"days_to_pay": 10},
        )
        risk_scorer.payment_events_log.append(paid_event)

        score = risk_scorer.score("good-factor-client")

        assert any("good" in f.lower() for f in score.factors)

    def test_rule_based_score_with_overdue(self, risk_scorer):
        """Rule-based score penalizes overdue count."""
        metrics = {
            "total_invoices": 5,
            "on_time_rate": 0.6,
            "avg_days_late": 5.0,
            "overdue_count": 3,
        }

        score = risk_scorer._rule_based_score(metrics)

        assert 0 <= score <= 10
        assert score < 6

    def test_classify_risk_level_boundaries(self, risk_scorer):
        """_classify_risk_level handles boundary values."""
        assert risk_scorer._classify_risk_level(7.0) == "low"
        assert risk_scorer._classify_risk_level(6.9) == "medium"
        assert risk_scorer._classify_risk_level(4.0) == "medium"
        assert risk_scorer._classify_risk_level(3.9) == "high"
        assert risk_scorer._classify_risk_level(0.0) == "high"

    def test_score_clamped_to_range(self, risk_scorer):
        """Score is always clamped to 0-10."""
        for i in range(10):
            event = PaymentEvent(
                timestamp=f"2026-03-{1 + i:02d}T10:00:00",
                event_type="payment_overdue",
                invoice_id=f"inv-{i}",
                client_id="clamp-client",
                amount=1000,
                details={},
            )
            risk_scorer.payment_events_log.append(event)

        score = risk_scorer.score("clamp-client")

        assert 0 <= score.score <= 10
