# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Ops Claw — Incident Analyzer

AI-powered incident analysis using the inference client.
Analyzes incoming alerts from webhooks and the mesh, generates
remediation recommendations, and triggers runbook execution.

Usage:
    analyzer = IncidentAnalyzer(inference_client, operational_log, dispatcher)
    result = analyzer.analyze_incident(alert)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .ops_init import OpsOperationalLog, OpsLogEntry

logger = logging.getLogger("milimo.ops.incident_analyzer")


@dataclass
class IncidentAnalysis:
    """Result of an incident analysis."""

    alert_id: str
    source: str
    severity: str
    title: str
    root_cause_hypothesis: str = ""
    recommended_actions: list[str] = field(default_factory=list)
    runbook_match: str = ""
    confidence: float = 0.0
    analyzed_at: str = ""

    def __post_init__(self) -> None:
        if not self.analyzed_at:
            self.analyzed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "source": self.source,
            "severity": self.severity,
            "title": self.title,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "recommended_actions": self.recommended_actions,
            "runbook_match": self.runbook_match,
            "confidence": self.confidence,
            "analyzed_at": self.analyzed_at,
        }


class IncidentAnalyzer:
    """
    AI-powered incident analyzer for the Ops Claw.

    Receives alerts from webhooks or mesh messages, uses inference
    to analyze root cause, recommends actions, and matches runbooks.
    """

    def __init__(
        self,
        inference_client: Any,
        operational_log: OpsOperationalLog,
        dispatcher: Any | None = None,
    ) -> None:
        self._inference = inference_client
        self._log = operational_log
        self._dispatcher = dispatcher
        self._analysis_history: list[IncidentAnalysis] = []

    def analyze_incident(self, alert: dict[str, Any]) -> IncidentAnalysis:
        """
        Analyze an incident alert using AI inference.

        Args:
            alert: Alert dict from webhook or mesh message with keys:
                - alert_id: str
                - source: str (sentry, vercel, uptime, generic)
                - severity: str (critical, warning, info)
                - title: str
                - description: str
                - raw_payload: dict (optional)

        Returns:
            IncidentAnalysis with root cause, recommended actions, runbook match.
        """
        alert_id = alert.get("alert_id", "unknown")
        source = alert.get("source", "unknown")
        severity = alert.get("severity", "warning")
        title = alert.get("title", "")
        alert.get("description", "")
        alert.get("raw_payload", {})

        logger.info("Analyzing incident %s from %s: %s", alert_id, source, title)

        try:
            analysis = self._run_inference_analysis(alert)
        except Exception as e:
            logger.warning(
                "AI analysis failed for %s, using rule-based fallback: %s", alert_id, e
            )
            analysis = self._rule_based_analysis(alert)

        self._analysis_history.append(analysis)

        self._log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="incident_analyzed",
                entity_id=alert_id,
                outcome="success",
                details={
                    "source": source,
                    "severity": severity,
                    "runbook_match": analysis.runbook_match,
                    "recommended_actions_count": len(analysis.recommended_actions),
                    "confidence": analysis.confidence,
                },
            )
        )

        logger.info(
            "Incident %s analyzed: runbook=%s, actions=%d, confidence=%.2f",
            alert_id,
            analysis.runbook_match,
            len(analysis.recommended_actions),
            analysis.confidence,
        )

        return analysis

    def _run_inference_analysis(self, alert: dict[str, Any]) -> IncidentAnalysis:
        """Use AI inference to analyze the incident."""
        prompt = self._build_analysis_prompt(alert)

        response = self._inference.complete(
            prompt=prompt,
            data_type="incident_analysis",
            temperature=0.2,
            system_prompt=(
                "You are an expert SRE incident analyzer. Analyze the alert and return "
                "a JSON object with: root_cause_hypothesis, recommended_actions (list), "
                "runbook_match (one of: restart_service, clear_cache, scale_up, rollback, "
                "investigate, notify_team, none), confidence (0.0-1.0)."
            ),
        )

        # Parse the JSON response
        try:
            # Handle markdown code blocks
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("\n", 1)[0]
                cleaned = cleaned.strip()

            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            # Fallback: parse from text
            data = self._extract_json_from_text(response)

        return IncidentAnalysis(
            alert_id=alert.get("alert_id", "unknown"),
            source=alert.get("source", "unknown"),
            severity=alert.get("severity", "warning"),
            title=alert.get("title", ""),
            root_cause_hypothesis=data.get(
                "root_cause_hypothesis", "Unable to determine"
            ),
            recommended_actions=data.get(
                "recommended_actions", ["Investigate further"]
            ),
            runbook_match=data.get("runbook_match", "investigate"),
            confidence=float(data.get("confidence", 0.5)),
        )

    def _rule_based_analysis(self, alert: dict[str, Any]) -> IncidentAnalysis:
        """Fallback rule-based analysis when inference is unavailable."""
        source = alert.get("source", "")
        severity = alert.get("severity", "warning")
        title = alert.get("title", "").lower()

        actions = []
        runbook = "investigate"
        confidence = 0.3

        if "out of memory" in title or "oom" in title:
            runbook = "restart_service"
            actions = [
                "Restart the affected service",
                "Check memory limits",
                "Review recent deployments",
            ]
            confidence = 0.7
        elif "connection" in title or "timeout" in title:
            runbook = "investigate"
            actions = [
                "Check network connectivity",
                "Verify service health",
                "Review load balancer logs",
            ]
            confidence = 0.5
        elif "deployment" in title and "fail" in title:
            runbook = "rollback"
            actions = [
                "Rollback to previous deployment",
                "Check deployment logs",
                "Verify build artifacts",
            ]
            confidence = 0.8
        elif "disk" in title or "storage" in title:
            runbook = "clear_cache"
            actions = ["Clear temporary files", "Check disk usage", "Archive old logs"]
            confidence = 0.6
        elif "cpu" in title or "load" in title:
            runbook = "scale_up"
            actions = [
                "Scale up instances",
                "Identify resource-intensive processes",
                "Check for runaway processes",
            ]
            confidence = 0.5

        if severity == "critical" and not actions:
            actions = [
                "Investigate immediately",
                "Notify on-call team",
                "Check service dashboards",
            ]

        return IncidentAnalysis(
            alert_id=alert.get("alert_id", "unknown"),
            source=source,
            severity=severity,
            title=alert.get("title", ""),
            root_cause_hypothesis=f"Rule-based analysis: {source} alert with severity {severity}",
            recommended_actions=actions,
            runbook_match=runbook,
            confidence=confidence,
        )

    def _build_analysis_prompt(self, alert: dict[str, Any]) -> str:
        """Build the analysis prompt for the inference client."""
        return f"""Analyze the following incident alert:

Source: {alert.get("source", "unknown")}
Severity: {alert.get("severity", "warning")}
Title: {alert.get("title", "")}
Description: {alert.get("description", "")}

Raw payload:
{json.dumps(alert.get("raw_payload", {}), indent=2)[:2000]}

Return a JSON object with:
- root_cause_hypothesis: A brief hypothesis about the root cause
- recommended_actions: A list of 2-4 recommended remediation actions
- runbook_match: One of [restart_service, clear_cache, scale_up, rollback, investigate, notify_team, none]
- confidence: A number between 0.0 and 1.0 indicating confidence in the analysis"""

    @staticmethod
    def _extract_json_from_text(text: str) -> dict:
        """Extract JSON from free-form text response."""
        import re

        # Try to find JSON object in text
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {
            "root_cause_hypothesis": "Analysis failed — investigate manually",
            "recommended_actions": ["Investigate the incident manually"],
            "runbook_match": "investigate",
            "confidence": 0.1,
        }

    def get_analysis_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent analysis results."""
        return [a.to_dict() for a in self._analysis_history[-limit:]]

    def get_critical_incidents(self) -> list[IncidentAnalysis]:
        """Return all critical severity incidents."""
        return [a for a in self._analysis_history if a.severity == "critical"]
