# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Finance Claw Pricing Engine.

Handles pricing queries from the Ops Claw.
SLA: Must respond within 10 minutes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
import json
import os

from .finance_init import (
    FinanceFilesystemInit,
    FinanceOperationalLog,
    FinanceLogEntry,
)
from .signal_dispatcher import FinanceSignalDispatcher


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
class PricingEstimate:
    """Pricing estimate for a project."""

    project_id: str
    scope_description: str
    complexity_estimate: str
    deadline: str
    estimated_hours: float
    recommended_rate: float
    floor_price: float
    ceiling_price: float
    scope_notes: str
    data_quality: str
    history_projects_used: int
    generated_at: str


COMPLEXITY_TO_HOURS = {
    "low": int(os.environ.get("MILIMO_HOURS_LOW", "8")),
    "medium": int(os.environ.get("MILIMO_HOURS_MEDIUM", "20")),
    "high": int(os.environ.get("MILIMO_HOURS_HIGH", "40")),
    "complex": int(os.environ.get("MILIMO_HOURS_COMPLEX", "80")),
}

RESPONSE_TIMEOUT_SECONDS = 540


class PricingEngine:
    """
    Handles pricing queries from the Ops Claw.

    SLA: Must respond within 10 minutes.
    If estimation takes longer: respond with rough estimate flagged
    data_quality="estimated". Never timeout silently.

    Calibrates estimates against historical project data from
    /sandbox/finance/pricing/history/.
    """

    def __init__(
        self,
        fs: FinanceFilesystemInit,
        inference_client: InferenceClient,
        dispatcher: FinanceSignalDispatcher,
        operational_log: FinanceOperationalLog,
    ):
        self.fs = fs
        self.inference_client = inference_client
        self.dispatcher = dispatcher
        self.operational_log = operational_log

    def handle_pricing_query(self, message: dict) -> PricingEstimate:
        """
        Handle a pricing_query message from Ops Claw.

        1. Extract: project_id, scope_description, complexity_estimate, deadline
        2. Load pricing rules from /sandbox/finance/pricing/rules.json
        3. Load historical estimates from pricing/history/
        4. Generate estimate via inference with data_type="scope_cost_estimation"
        5. Apply floor/ceiling from rules.json
        6. Write estimate to pricing/estimates/{project_id}.json
        7. Send pricing_response via dispatcher
        8. Log: action_type="pricing_query_answered"
        9. Return PricingEstimate

        If inference fails or times out:
        Use rule-based fallback estimate
        Set data_quality="estimated"
        Still respond — never miss the SLA
        """
        project_id = message.get("project_id", "")
        scope_description = message.get("scope_description", "")
        complexity_estimate = message.get("complexity_estimate", "medium")
        deadline = message.get("deadline", "")

        rules = self.load_pricing_rules()
        historical = self.load_historical_calibration(complexity_estimate)

        estimate: PricingEstimate
        try:
            prompt = self._build_estimation_prompt(
                scope_description, complexity_estimate, deadline, historical, rules
            )
            inference_output = self.inference_client.complete(
                prompt=prompt,
                data_type="scope_cost_estimation",
                max_tokens=800,
            )

            parsed = self._parse_inference_output(inference_output, rules)
            estimated_hours = parsed.get(
                "estimated_hours", COMPLEXITY_TO_HOURS.get(complexity_estimate, 20)
            )
            recommended_rate = parsed.get(
                "recommended_rate", rules.get("default_hourly_rate", 100)
            )
            scope_notes = parsed.get("scope_notes", scope_description)

            floor_price = (
                estimated_hours * recommended_rate * rules.get("floor_multiplier", 0.8)
            )
            ceiling_price = (
                estimated_hours
                * recommended_rate
                * rules.get("ceiling_multiplier", 1.5)
            )

            estimate = PricingEstimate(
                project_id=project_id,
                scope_description=scope_description,
                complexity_estimate=complexity_estimate,
                deadline=deadline,
                estimated_hours=estimated_hours,
                recommended_rate=recommended_rate,
                floor_price=round(floor_price, 2),
                ceiling_price=round(ceiling_price, 2),
                scope_notes=scope_notes,
                data_quality="complete" if historical else "estimated",
                history_projects_used=len(historical),
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            estimate = self._rule_based_fallback(
                scope_description, complexity_estimate, rules
            )
            estimate.project_id = project_id
            estimate.deadline = deadline
            estimate.scope_description = scope_description

        estimate_path = self.fs.get_pricing_estimate_path(project_id)
        estimate_path.parent.mkdir(parents=True, exist_ok=True)
        estimate_path.write_text(json.dumps(self._estimate_to_dict(estimate), indent=2))

        self.dispatcher.send_pricing_response(
            project_id=project_id,
            floor_price=estimate.floor_price,
            ceiling_price=estimate.ceiling_price,
            scope_notes=estimate.scope_notes,
            data_quality=estimate.data_quality,
        )

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pricing_query_answered",
            entity_id=project_id,
            amount=estimate.floor_price,
            outcome="success",
            details={
                "data_quality": estimate.data_quality,
                "history_used": estimate.history_projects_used,
            },
        )
        self.operational_log.append(entry)

        return estimate

    def load_pricing_rules(self) -> dict:
        """
        Read pricing/rules.json.

        Return dict with default_hourly_rate, floor_multiplier,
        ceiling_multiplier, scope_weights.
        Return defaults if file is empty or missing keys.
        """
        rules_path = self.fs.base / "pricing" / "rules.json"
        defaults = {
            "default_hourly_rate": float(os.environ.get("MILIMO_HOURLY_RATE", "100")),
            "floor_multiplier": float(os.environ.get("MILIMO_FLOOR_MULTIPLIER", "0.8")),
            "ceiling_multiplier": float(
                os.environ.get("MILIMO_CEILING_MULTIPLIER", "1.5")
            ),
            "scope_weights": {},
            "last_updated": None,
        }

        if not rules_path.exists():
            return defaults

        try:
            data = json.loads(rules_path.read_text())
            return {**defaults, **data}
        except (json.JSONDecodeError, Exception):
            return defaults

    def load_historical_calibration(
        self, complexity: str, max_projects: int = 10
    ) -> list[dict]:
        """
        Read pricing/history/*.json.

        Filter to similar complexity.
        Return list of {estimated_hours, actual_hours, accuracy_pct}.
        Used to calibrate current estimate.
        """
        history_dir = self.fs.base / "pricing" / "history"
        if not history_dir.exists():
            return []

        results: list[dict] = []
        for path in sorted(history_dir.glob("*.json"), reverse=True)[
            : max_projects * 2
        ]:
            try:
                data = json.loads(path.read_text())
                if data.get("complexity_estimate") == complexity:
                    results.append(
                        {
                            "estimated_hours": data.get("estimated_hours", 0),
                            "actual_hours": data.get("actual_hours", 0),
                            "accuracy_pct": data.get("accuracy_pct", 100),
                        }
                    )
                    if len(results) >= max_projects:
                        break
            except (json.JSONDecodeError, Exception):
                continue

        return results

    def _rule_based_fallback(
        self,
        scope_description: str,
        complexity_estimate: str,
        rules: dict,
    ) -> PricingEstimate:
        """
        Pure rule-based estimate when inference unavailable.

        complexity_to_hours = {low: 8, medium: 20, high: 40, complex: 80}
        Multiply by default_hourly_rate
        Apply floor/ceiling multipliers
        data_quality = "estimated"
        """
        hours = COMPLEXITY_TO_HOURS.get(complexity_estimate, 20)
        rate = rules.get("default_hourly_rate", 100)
        floor_mult = rules.get("floor_multiplier", 0.8)
        ceiling_mult = rules.get("ceiling_multiplier", 1.5)

        floor_price = hours * rate * floor_mult
        ceiling_price = hours * rate * ceiling_mult

        return PricingEstimate(
            project_id="",
            scope_description=scope_description,
            complexity_estimate=complexity_estimate,
            deadline="",
            estimated_hours=hours,
            recommended_rate=rate,
            floor_price=round(floor_price, 2),
            ceiling_price=round(ceiling_price, 2),
            scope_notes=f"Rule-based estimate for {complexity_estimate} complexity",
            data_quality="estimated",
            history_projects_used=0,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_estimation_prompt(
        self,
        scope: str,
        complexity: str,
        deadline: str,
        calibration_data: list[dict],
        rules: dict,
    ) -> str:
        """
        Structured prompt for scope cost estimation.

        Include calibration data as examples if available.
        """
        calibration_section = ""
        if calibration_data:
            calibration_section = "\nHistorical calibration data:\n"
            for i, item in enumerate(calibration_data[:5], 1):
                calibration_section += f"{i}. Estimated {item['estimated_hours']}h, Actual {item['actual_hours']}h ({item['accuracy_pct']}% accuracy)\n"

        return f"""Analyze this project scope and provide a pricing estimate.

Scope: {scope}
Complexity: {complexity}
Deadline: {deadline}
Default hourly rate: ${rules.get("default_hourly_rate", 100)}
{calibration_section}

Provide your response as JSON:
{{
    "estimated_hours": <number>,
    "recommended_rate": <number>,
    "scope_notes": "<brief notes about assumptions>"
}}"""

    def _parse_inference_output(self, output: str, rules: dict) -> dict:
        """Parse inference output into structured dict."""
        import re

        json_match = re.search(r"\{[^}]+\}", output, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        hours_match = re.search(
            r"estimated_hours[\"']?\s*[:=]\s*(\d+(?:\.\d+)?)", output
        )
        rate_match = re.search(
            r"recommended_rate[\"']?\s*[:=]\s*(\d+(?:\.\d+)?)", output
        )

        return {
            "estimated_hours": float(hours_match.group(1))
            if hours_match
            else COMPLEXITY_TO_HOURS.get("medium", 20),
            "recommended_rate": float(rate_match.group(1))
            if rate_match
            else rules.get("default_hourly_rate", 100),
            "scope_notes": "Parsed from inference output",
        }

    def _estimate_to_dict(self, estimate: PricingEstimate) -> dict:
        """Convert PricingEstimate to dict."""
        return {
            "project_id": estimate.project_id,
            "scope_description": estimate.scope_description,
            "complexity_estimate": estimate.complexity_estimate,
            "deadline": estimate.deadline,
            "estimated_hours": estimate.estimated_hours,
            "recommended_rate": estimate.recommended_rate,
            "floor_price": estimate.floor_price,
            "ceiling_price": estimate.ceiling_price,
            "scope_notes": estimate.scope_notes,
            "data_quality": estimate.data_quality,
            "history_projects_used": estimate.history_projects_used,
            "generated_at": estimate.generated_at,
        }

    def update_actual_cost(
        self, project_id: str, actual_hours: float, actual_cost: float
    ) -> None:
        """
        Write actual vs estimated to pricing/history/{project_id}.json.

        Called when project delivers — used for future calibration.
        """
        estimate_path = self.fs.get_pricing_estimate_path(project_id)
        if not estimate_path.exists():
            return

        estimate_data = json.loads(estimate_path.read_text())
        estimated_hours = estimate_data.get("estimated_hours", 0)

        accuracy = 100.0
        if estimated_hours > 0:
            accuracy = 100 - abs(
                (actual_hours - estimated_hours) / estimated_hours * 100
            )
            accuracy = max(0, min(100, accuracy))

        history_path = self.fs.get_pricing_history_path(project_id)
        history_path.parent.mkdir(parents=True, exist_ok=True)

        history_data = {
            **estimate_data,
            "actual_hours": actual_hours,
            "actual_cost": actual_cost,
            "accuracy_pct": round(accuracy, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        history_path.write_text(json.dumps(history_data, indent=2))

        entry = FinanceLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="pricing_history_updated",
            entity_id=project_id,
            amount=actual_cost,
            outcome="success",
            details={"accuracy_pct": accuracy},
        )
        self.operational_log.append(entry)
