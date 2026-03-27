#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Client Health Scorer

Scores client relationship health weekly.

Inputs: comms.log (response times), decisions.log (revision requests),
project status files (scope adherence), inference sentiment analysis.
Sends client_health_signal to Analytics Claw for all clients.
Flags at_risk clients (score < 6.0) in War Room immediately.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ops_init import OpsFilesystemInit, OpsOperationalLog, OpsLogEntry, OpsCommsLog
from .signal_dispatcher import OpsSignalDispatcher
from .approval_handler import OpsApprovalHandler

logger = logging.getLogger("milimo.ops")


@dataclass
class ClientHealthScore:
    """Health score for a client relationship."""

    client_id: str
    score: float
    health_level: str  # "healthy" | "monitor" | "at_risk"
    factors: list[str] = field(default_factory=list)
    response_time_avg_hrs: float = 0.0
    revision_request_rate: float = 0.0
    scope_adherence_score: float = 0.0
    communication_sentiment: float = 0.0
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "score": self.score,
            "health_level": self.health_level,
            "factors": self.factors,
            "response_time_avg_hrs": self.response_time_avg_hrs,
            "revision_request_rate": self.revision_request_rate,
            "scope_adherence_score": self.scope_adherence_score,
            "communication_sentiment": self.communication_sentiment,
            "scored_at": self.scored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientHealthScore:
        return cls(
            client_id=data["client_id"],
            score=data["score"],
            health_level=data["health_level"],
            factors=data.get("factors", []),
            response_time_avg_hrs=data.get("response_time_avg_hrs", 0.0),
            revision_request_rate=data.get("revision_request_rate", 0.0),
            scope_adherence_score=data.get("scope_adherence_score", 0.0),
            communication_sentiment=data.get("communication_sentiment", 0.0),
            scored_at=data.get("scored_at", ""),
        )


class ClientHealthScorer:
    """
    Scores client relationship health weekly.

    Inputs: comms.log (response times), decisions.log (revision requests),
    project status files (scope adherence), inference sentiment analysis.
    Sends client_health_signal to Analytics Claw for all clients.
    Flags at_risk clients (score < 6.0) in War Room immediately.
    """

    AT_RISK_THRESHOLD = 6.0
    HEALTHY_THRESHOLD = 8.0

    def __init__(
        self,
        fs: OpsFilesystemInit,
        inference_client: Any,
        dispatcher: OpsSignalDispatcher,
        approval_handler: OpsApprovalHandler,
        operational_log: OpsOperationalLog,
        comms_log: OpsCommsLog,
        decisions_log_path: Path | None = None,
    ):
        self._fs = fs
        self._inference_client = inference_client
        self._dispatcher = dispatcher
        self._approval_handler = approval_handler
        self._operational_log = operational_log
        self._comms_log = comms_log
        self._decisions_log_path = decisions_log_path or fs._base / "logs" / "decisions.log"

    def score_client(self, client_id: str) -> ClientHealthScore:
        response_time_score = self._calculate_response_time_score(client_id)
        revision_rate_score = self._calculate_revision_rate_score(client_id)
        scope_adherence_score = self._calculate_scope_adherence_score(client_id)
        sentiment_score = self._calculate_sentiment_score(client_id)

        combined_score = self._combine_scores(
            response_time_score,
            revision_rate_score,
            scope_adherence_score,
            sentiment_score,
        )

        factors: list[str] = []
        if response_time_score < 6.0:
            factors.append("Slow response times")
        if revision_rate_score < 6.0:
            factors.append("High revision request rate")
        if scope_adherence_score < 6.0:
            factors.append("Scope creep issues")
        if sentiment_score < 6.0:
            factors.append("Negative communication sentiment")

        if combined_score >= self.HEALTHY_THRESHOLD:
            health_level = "healthy"
        elif combined_score >= self.AT_RISK_THRESHOLD:
            health_level = "monitor"
        else:
            health_level = "at_risk"

        health_score = ClientHealthScore(
            client_id=client_id,
            score=combined_score,
            health_level=health_level,
            factors=factors,
            response_time_avg_hrs=self._get_avg_response_time(client_id),
            revision_request_rate=self._get_revision_rate(client_id),
            scope_adherence_score=scope_adherence_score,
            communication_sentiment=sentiment_score,
        )

        self._dispatcher.send_client_health_signal(
            client_id=client_id,
            health_score=combined_score,
            health_factors=factors,
            recommended_action=self._get_recommended_action(health_level),
        )

        if combined_score < self.AT_RISK_THRESHOLD:
            self._approval_handler.queue_review(
                action_type="client_at_risk",
                entity_id=client_id,
                content=f"Client {client_id} health score is {combined_score:.1f} (< 6.0 threshold).\n\n"
                f"Factors: {', '.join(factors)}\n\n"
                f"Recommended action: {self._get_recommended_action(health_level)}",
                context={
                    "health_score": combined_score,
                    "factors": factors,
                },
            )

        self._operational_log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="client_scored",
                entity_id=client_id,
                outcome="success",
                details={
                    "score": combined_score,
                    "health_level": health_level,
                    "factors": factors,
                },
            )
        )

        return health_score

    def score_all_active_clients(self) -> list[ClientHealthScore]:
        active_clients = self._fs.get_active_clients()
        scores: list[ClientHealthScore] = []

        for client_id in active_clients:
            try:
                score = self.score_client(client_id)
                scores.append(score)
            except Exception as e:
                logger.error("Failed to score client %s: %s", client_id, e)

        return scores

    def _calculate_response_time_score(self, client_id: str) -> float:
        response_times = self._comms_log.get_response_times(client_id)

        if not response_times:
            return 7.0

        avg_hours = sum(response_times) / len(response_times)

        if avg_hours <= 4:
            return 10.0
        elif avg_hours <= 12:
            return 8.0
        elif avg_hours <= 24:
            return 6.0
        elif avg_hours <= 48:
            return 4.0
        else:
            return 2.0

    def _calculate_revision_rate_score(self, client_id: str) -> float:
        revision_count = self._count_revision_requests(client_id)
        total_deliverables = self._count_deliverables(client_id)

        if total_deliverables == 0:
            return 7.0

        revision_rate = revision_count / total_deliverables

        if revision_rate <= 0.1:
            return 10.0
        elif revision_rate <= 0.25:
            return 8.0
        elif revision_rate <= 0.5:
            return 6.0
        elif revision_rate <= 0.75:
            return 4.0
        else:
            return 2.0

    def _calculate_scope_adherence_score(self, client_id: str) -> float:
        scope_creep_count = self._count_scope_creep_events(client_id)

        if scope_creep_count == 0:
            return 10.0
        elif scope_creep_count == 1:
            return 7.0
        elif scope_creep_count == 2:
            return 5.0
        else:
            return 3.0

    def _calculate_sentiment_score(self, client_id: str) -> float:
        history = self._comms_log.get_client_history(client_id, days=30)

        if not history:
            return 7.0

        recent_messages = [e for e in history if e.direction == "received"][-5:]
        if not recent_messages:
            return 7.0

        content_preview = " ".join(e.content_preview for e in recent_messages)

        prompt = f"""Analyze the sentiment of this client communication history.

COMMUNICATION HISTORY:
{content_preview}

Score the sentiment from 0-10:
0 = Very negative (angry, threatening to leave)
10 = Very positive (enthusiastic, praising)

Respond in JSON format:
{{"sentiment_score": X, "indicators": ["indicator1", "indicator2"]}}"""

        try:
            response = self._inference_client.complete(
                prompt=prompt,
                data_type="communication_sentiment_analysis",
                max_tokens=100,
            )

            match = re.search(r"\{[^}]+\}", response)
            if match:
                data = json.loads(match.group())
                return float(data.get("sentiment_score", 7.0))
        except Exception as e:
            logger.warning("Sentiment analysis failed: %s", e)

        return 7.0

    def _combine_scores(
        self,
        response_time: float,
        revision_rate: float,
        scope_adherence: float,
        sentiment: float,
    ) -> float:
        combined = (
            response_time * 0.3
            + revision_rate * 0.25
            + scope_adherence * 0.25
            + sentiment * 0.2
        )
        return max(0.0, min(10.0, combined))

    def _get_avg_response_time(self, client_id: str) -> float:
        response_times = self._comms_log.get_response_times(client_id)
        if not response_times:
            return 0.0
        return sum(response_times) / len(response_times)

    def _get_revision_rate(self, client_id: str) -> float:
        revision_count = self._count_revision_requests(client_id)
        total_deliverables = self._count_deliverables(client_id)
        if total_deliverables == 0:
            return 0.0
        return revision_count / total_deliverables

    def _count_revision_requests(self, client_id: str) -> int:
        if not self._decisions_log_path.exists():
            return 0

        count = 0
        try:
            with self._decisions_log_path.open("r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("action_type") == "revision_request":
                            if entry.get("context", {}).get("client_id") == client_id:
                                count += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        return count

    def _count_deliverables(self, client_id: str) -> int:
        count = 0
        active_dir = self._fs._base / "active" / client_id / "projects"
        if not active_dir.exists():
            return count

        for project_dir in active_dir.iterdir():
            if project_dir.is_dir():
                status_file = project_dir / "status.json"
                status_data = self._fs.read_json(status_file)
                if status_data and status_data.get("deliverable_received"):
                    count += 1

        return count

    def _count_scope_creep_events(self, client_id: str) -> int:
        count = 0
        if not self._decisions_log_path.exists():
            return count

        try:
            with self._decisions_log_path.open("r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("action_type") == "scope_change_order":
                            if entry.get("entity_id", "").startswith(client_id):
                                count += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

        return count

    def _get_recommended_action(self, health_level: str) -> str:
        if health_level == "at_risk":
            return "Schedule check-in call, review recent issues, offer remediation"
        elif health_level == "monitor":
            return "Increase communication frequency, proactively address concerns"
        else:
            return "Continue current engagement approach"
