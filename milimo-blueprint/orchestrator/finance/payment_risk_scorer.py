# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Payment Risk Scorer.

Scores client payment risk before invoice is shown to operator.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from .finance_init import PaymentEventsLog


class InferenceClient(Protocol):
    """Protocol for inference client."""

    def complete(
        self,
        prompt: str,
        data_type: str,
        max_tokens: int = 800,
    ) -> str:
        """Complete a prompt with the model."""
        ...


@dataclass
class PaymentRiskScore:
    """Payment risk score for a client."""

    client_id: str
    score: float
    risk_level: str
    factors: list[str]
    invoices_analyzed: int
    on_time_rate: float
    avg_days_late: float
    overdue_count: int
    data_quality: str


class PaymentRiskScorer:
    """
    Scores client payment risk before invoice is shown to operator.

    Reads from payment-events.log — client's historical payment behavior.
    No external API calls — purely internal signal.
    New clients with no history get score=5.0 (neutral), data_quality="no_history".
    """

    def __init__(
        self,
        payment_events_log: PaymentEventsLog,
        inference_client: InferenceClient,
    ):
        self.payment_events_log = payment_events_log
        self.inference_client = inference_client

    def score(self, client_id: str) -> PaymentRiskScore:
        """
        Score a client's payment risk.

        1. Load client payment history from payment-events.log
        2. If no history: return neutral score (5.0, "medium", "no_history")
        3. Calculate: on_time_rate, avg_days_late, overdue_count
        4. Generate score via inference with data_type="payment_risk_scoring"
        5. Classify risk_level from score
        6. Return PaymentRiskScore
        """
        history = self.payment_events_log.get_client_history(client_id)

        if not history:
            return PaymentRiskScore(
                client_id=client_id,
                score=5.0,
                risk_level="medium",
                factors=["No payment history"],
                invoices_analyzed=0,
                on_time_rate=1.0,
                avg_days_late=0.0,
                overdue_count=0,
                data_quality="no_history",
            )

        metrics = self._calculate_payment_metrics(history)

        prompt = self._build_scoring_prompt(client_id, metrics)

        try:
            output = self.inference_client.complete(
                prompt=prompt,
                data_type="payment_risk_scoring",
                max_tokens=400,
            )
            score = self._parse_score(output)
        except Exception:
            score = self._rule_based_score(metrics)

        risk_level = self._classify_risk_level(score)

        factors = self._generate_factors(metrics, risk_level)

        return PaymentRiskScore(
            client_id=client_id,
            score=score,
            risk_level=risk_level,
            factors=factors,
            invoices_analyzed=metrics["total_invoices"],
            on_time_rate=metrics["on_time_rate"],
            avg_days_late=metrics["avg_days_late"],
            overdue_count=metrics["overdue_count"],
            data_quality="complete",
        )

    def _calculate_payment_metrics(self, history: list) -> dict:
        """
        Calculate payment metrics from history.

        Calculate: on_time_rate, avg_days_late, overdue_count
        from payment-events.log records for this client.
        """
        total_invoices = 0
        on_time = 0
        total_days_late = 0.0
        overdue_count = 0

        for event in history:
            if event.event_type == "invoice_sent":
                total_invoices += 1
            elif event.event_type == "payment_received":
                days = event.details.get("days_to_pay", 0)
                if days <= 14:
                    on_time += 1
                total_days_late += max(0, days - 14)
            elif event.event_type == "payment_overdue":
                overdue_count += 1

        on_time_rate = on_time / total_invoices if total_invoices > 0 else 1.0
        avg_days_late = total_days_late / total_invoices if total_invoices > 0 else 0.0

        return {
            "total_invoices": total_invoices,
            "on_time_rate": on_time_rate,
            "avg_days_late": avg_days_late,
            "overdue_count": overdue_count,
        }

    def _classify_risk_level(self, score: float) -> str:
        """
        Classify risk level from score.

        7.0–10.0: "low"
        4.0–7.0: "medium"
        0.0–4.0: "high"
        """
        if score >= 7.0:
            return "low"
        elif score >= 4.0:
            return "medium"
        else:
            return "high"

    def _build_scoring_prompt(self, client_id: str, metrics: dict) -> str:
        """Build prompt for payment risk scoring."""
        return f"""Score this client's payment risk (0-10, higher is safer).

Client: {client_id}
Total Invoices: {metrics['total_invoices']}
On-Time Rate: {metrics['on_time_rate']:.1%}
Average Days Late: {metrics['avg_days_late']:.1f}
Overdue Count: {metrics['overdue_count']}

Return only a number between 0 and 10."""

    def _parse_score(self, output: str) -> float:
        """Parse score from inference output."""
        import re

        match = re.search(r"(\d+(?:\.\d+)?)", output)
        if match:
            return float(match.group(1))
        return 5.0

    def _rule_based_score(self, metrics: dict) -> float:
        """Calculate rule-based score when inference fails."""
        on_time_rate = metrics["on_time_rate"]
        overdue_count = metrics["overdue_count"]

        base = on_time_rate * 10

        if overdue_count >= 3:
            base -= 3
        elif overdue_count >= 2:
            base -= 2
        elif overdue_count >= 1:
            base -= 1

        return max(0.0, min(10.0, base))

    def _generate_factors(self, metrics: dict, risk_level: str) -> list[str]:
        """Generate plain-English risk factors."""
        factors: list[str] = []

        if metrics["on_time_rate"] < 0.8:
            factors.append(f"Low on-time rate ({metrics['on_time_rate']:.0%})")
        if metrics["overdue_count"] >= 2:
            factors.append(f"Multiple overdue invoices ({metrics['overdue_count']})")
        if metrics["avg_days_late"] > 7:
            factors.append(f"Average {metrics['avg_days_late']:.0f} days late")

        if not factors:
            factors.append("Good payment history")

        return factors
