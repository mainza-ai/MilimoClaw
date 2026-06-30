# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Query Handler

Handles on-demand queries from other claws.
Enforces 2-minute SLA for all responses.
Never times out silently — always responds.
"""

from __future__ import annotations

import json
import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Literal

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
)

logger = logging.getLogger("milimo.query_handler")


class QueryTimeoutError(Exception):
    """Raised when query processing exceeds the SLA timeout."""

    pass


@dataclass
class QueryResponse:
    """Response to a query from another claw."""

    query_id: str
    query_type: str
    responding_to: str
    requesting_claw: str
    data_quality: str  # "complete", "partial", "estimated", "insufficient"
    data: dict[str, Any] | None
    generated_at: str
    processing_time_ms: int
    days_collected: int | None = None
    days_needed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "responding_to": self.responding_to,
            "requesting_claw": self.requesting_claw,
            "data_quality": self.data_quality,
            "data": self.data,
            "generated_at": self.generated_at,
            "processing_time_ms": self.processing_time_ms,
        }
        if self.days_collected is not None:
            result["days_collected"] = self.days_collected
        if self.days_needed is not None:
            result["days_needed"] = self.days_needed
        return result


class QueryHandler:
    """
    Handles on-demand queries from other claws.

    SLA: 2-minute maximum response time — enforced by timeout wrapper.
    Never returns without a response. If data unavailable, returns
    data_quality="insufficient" with days_collected and days_needed.

    Logs SLA violations to both operational.log and signals.log.
    """

    RESPONSE_TIMEOUT_SECONDS = 110
    SLA_VIOLATION_THRESHOLD_MS = 120000  # 2 minutes in milliseconds
    MIN_DAYS_FOR_COMPLETE = 7

    def __init__(
        self,
        fs: AnalyticsFilesystemInit,
        operational_log: AnalyticsOperationalLog,
    ) -> None:
        self.fs = fs
        self.operational_log = operational_log
        self._queries_log_path = fs.get_log_path("queries.log")
        self._queries_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._queries_log_path.exists():
            self._queries_log_path.touch()

        self._signals_log_path = fs.get_log_path("signals.log")
        self._signals_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._signals_log_path.exists():
            self._signals_log_path.touch()

    def _log_to_queries_log(self, entry: dict[str, Any]) -> None:
        """Write entry to queries.log."""
        try:
            with open(self._queries_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
        except Exception as e:
            logger.warning("Failed to write to queries.log: %s", e)

    def _log_to_signals_log(self, entry: dict[str, Any]) -> None:
        """Write entry to signals.log for SLA violations."""
        try:
            with open(self._signals_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
        except Exception as e:
            logger.warning("Failed to write to signals.log: %s", e)

    def _log_sla_violation(
        self,
        query_id: str,
        message_type: str,
        requesting_claw: str,
        elapsed_ms: int,
    ) -> None:
        """
        Log SLA violation to both operational.log and signals.log.

        Called when query processing exceeds SLA_VIOLATION_THRESHOLD_MS.
        Does NOT prevent response from being sent.
        """
        violation_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_id": query_id,
            "query_type": message_type,
            "requesting_claw": requesting_claw,
            "event": "sla_violation",
            "elapsed_ms": elapsed_ms,
            "sla_threshold_ms": self.SLA_VIOLATION_THRESHOLD_MS,
            "overage_ms": elapsed_ms - self.SLA_VIOLATION_THRESHOLD_MS,
        }

        self._log_to_signals_log(violation_entry)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="query_sla_violation",
                entity_id=query_id,
                source_claw=requesting_claw,
                outcome="sla_exceeded",
                details={
                    "message_type": message_type,
                    "elapsed_ms": elapsed_ms,
                    "sla_threshold_ms": self.SLA_VIOLATION_THRESHOLD_MS,
                    "overage_ms": elapsed_ms - self.SLA_VIOLATION_THRESHOLD_MS,
                },
            )
        )

        logger.warning(
            "Query SLA violation: %s took %dms (SLA: %dms)",
            query_id,
            elapsed_ms,
            self.SLA_VIOLATION_THRESHOLD_MS,
        )

    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout."""
        raise QueryTimeoutError("Query processing exceeded timeout")

    def _with_timeout(
        self, func, timeout_seconds: int, *args, **kwargs
    ) -> tuple[Any, bool]:
        """
        Execute function with timeout enforcement.

        Returns (result, timed_out) tuple.
        """
        result = None
        timed_out = False

        try:
            old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(timeout_seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except QueryTimeoutError:
            timed_out = True
        except Exception:
            raise

        return result, timed_out

    def handle(self, raw_message: dict[str, Any]) -> QueryResponse:
        """
        Route to correct handler by message_type.

        Enforces RESPONSE_TIMEOUT_SECONDS — if exceeded, returns partial response.
        Logs query receipt and response dispatch to queries.log.
        """
        query_id = raw_message.get("message_id", "unknown")
        message_type = raw_message.get("message_type", "")
        requesting_claw = raw_message.get("sender_role", "unknown")

        start_time = time.monotonic()

        query_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_id": query_id,
            "query_type": message_type,
            "requesting_claw": requesting_claw,
            "status": "received",
        }
        self._log_to_queries_log(query_entry)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="query_received",
                entity_id=query_id,
                source_claw=requesting_claw,
                outcome="processing",
                details={"message_type": message_type},
            )
        )

        try:
            result, timed_out = self._with_timeout(
                self._process_query,
                self.RESPONSE_TIMEOUT_SECONDS,
                raw_message,
            )

            if timed_out:
                logger.warning(
                    "Query %s timed out, returning partial response", query_id
                )
                response = QueryResponse(
                    query_id=query_id,
                    query_type=message_type,
                    responding_to=raw_message.get("message_id", ""),
                    requesting_claw=requesting_claw,
                    data_quality="partial",
                    data={
                        "error": "Query processing timed out",
                        "partial_result": result.data
                        if result and hasattr(result, "data")
                        else None,
                    },
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    processing_time_ms=int((time.monotonic() - start_time) * 1000),
                )
            else:
                response = result
        except Exception as e:
            logger.exception("Query %s failed: %s", query_id, e)
            response = QueryResponse(
                query_id=query_id,
                query_type=message_type,
                responding_to=raw_message.get("message_id", ""),
                requesting_claw=requesting_claw,
                data_quality="error",
                data={"error": str(e)},
                generated_at=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=int((time.monotonic() - start_time) * 1000),
            )

        response.processing_time_ms = int((time.monotonic() - start_time) * 1000)

        sla_exceeded = response.processing_time_ms > self.SLA_VIOLATION_THRESHOLD_MS

        if sla_exceeded:
            self._log_sla_violation(
                query_id=query_id,
                message_type=message_type,
                requesting_claw=requesting_claw,
                elapsed_ms=response.processing_time_ms,
            )

        response_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_id": query_id,
            "query_type": message_type,
            "requesting_claw": requesting_claw,
            "status": "responded",
            "data_quality": response.data_quality,
            "processing_time_ms": response.processing_time_ms,
            "sla_exceeded": sla_exceeded,
        }
        self._log_to_queries_log(response_entry)

        self.operational_log.append(
            AnalyticsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="query_answered",
                entity_id=query_id,
                source_claw=requesting_claw,
                outcome="success"
                if response.data_quality not in ["error", "partial"]
                else "failed",
                details={
                    "data_quality": response.data_quality,
                    "processing_time_ms": response.processing_time_ms,
                },
            )
        )

        return response

    def _process_query(self, raw_message: dict[str, Any]) -> QueryResponse:
        """Internal query processing without timeout handling."""
        query_id = raw_message.get("message_id", "unknown")
        message_type = raw_message.get("message_type", "")
        requesting_claw = raw_message.get("sender_role", "unknown")

        if message_type == "content_performance_query":
            return self.handle_content_performance_query(
                query=raw_message.get("payload", {}).get("query", ""),
                lookback_days=raw_message.get("payload", {}).get("lookback_days", 7),
                platform=raw_message.get("payload", {}).get("platform"),
                requesting_claw=requesting_claw,
                query_id=query_id,
            )
        elif message_type == "behavior_query":
            return self.handle_behavior_query(
                query=raw_message.get("payload", {}).get("query", ""),
                feature_id=raw_message.get("payload", {}).get("feature_id"),
                lookback_days=raw_message.get("payload", {}).get("lookback_days", 14),
                requesting_claw=requesting_claw,
                query_id=query_id,
            )
        else:
            return QueryResponse(
                query_id=query_id,
                query_type=message_type,
                responding_to=raw_message.get("message_id", ""),
                requesting_claw=requesting_claw,
                data_quality="error",
                data={"error": f"Unknown query type: {message_type}"},
                generated_at=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=0,
            )

    def handle_content_performance_query(
        self,
        query: str,
        lookback_days: int,
        platform: str | None,
        requesting_claw: str,
        query_id: str,
    ) -> QueryResponse:
        """
        Handle content performance query.

        Returns top formats sorted by engagement.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        data_dir = self.fs.get_data_path("content-performance")

        format_engagement: dict[str, list[float]] = {}
        days_with_data: set[str] = set()

        if data_dir.exists():
            for platform_dir in data_dir.iterdir():
                if not platform_dir.is_dir():
                    continue
                if platform and platform_dir.name != platform:
                    continue

                for month_dir in platform_dir.iterdir():
                    if not month_dir.is_dir():
                        continue

                    perf_file = month_dir / "performance.jsonl"
                    if not perf_file.exists():
                        continue

                    try:
                        with open(perf_file) as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    record = json.loads(line)
                                    received_at = record.get("received_at", "")
                                    try:
                                        record_time = datetime.fromisoformat(
                                            received_at
                                        )
                                        if record_time < cutoff:
                                            continue
                                        days_with_data.add(received_at[:10])
                                    except ValueError:
                                        continue

                                    content_type = record.get("content_type", "unknown")
                                    engagement_data = record.get("engagement_data", {})
                                    engagement_rate = engagement_data.get(
                                        "engagement_rate"
                                    )
                                    if isinstance(engagement_rate, (int, float)):
                                        if content_type not in format_engagement:
                                            format_engagement[content_type] = []
                                        format_engagement[content_type].append(
                                            float(engagement_rate)
                                        )

                                except json.JSONDecodeError:
                                    continue
                    except Exception as e:
                        logger.warning("Failed to read %s: %s", perf_file, e)

        days_collected = len(days_with_data)

        if days_collected < self.MIN_DAYS_FOR_COMPLETE:
            return self._insufficient_response(
                query_id=query_id,
                query_type="content_performance_query",
                requesting_claw=requesting_claw,
                days_collected=days_collected,
                days_needed=self.MIN_DAYS_FOR_COMPLETE,
            )

        top_formats = []
        for content_type, rates in format_engagement.items():
            if rates:
                avg_engagement = sum(rates) / len(rates)
                top_formats.append(
                    {
                        "format": content_type,
                        "avg_engagement": round(avg_engagement, 4),
                        "sample_count": len(rates),
                    }
                )

        top_formats.sort(key=lambda x: x["avg_engagement"], reverse=True)
        top_formats = top_formats[:10]

        return QueryResponse(
            query_id=str(hash(query_id) % 10000),
            query_type="content_performance_query",
            responding_to=query_id,
            requesting_claw=requesting_claw,
            data_quality="complete",
            data={
                "top_formats": top_formats,
                "lookback_days": lookback_days,
                "platform_filter": platform,
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=0,
            days_collected=days_collected,
            days_needed=self.MIN_DAYS_FOR_COMPLETE,
        )

    def handle_behavior_query(
        self,
        query: str,
        feature_id: str | None,
        lookback_days: int,
        requesting_claw: str,
        query_id: str,
    ) -> QueryResponse:
        """
        Handle behavior query from Build Claw.

        Correlates feature shipping with client health changes.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        delivery_path = self.fs.get_data_path("delivery-velocity", "velocity.jsonl")
        health_dir = self.fs.get_data_path("client-health")

        feature_data: list[dict[str, Any]] = []
        health_changes: list[dict[str, Any]] = []
        days_with_data: set[str] = set()

        if delivery_path.exists():
            try:
                with open(delivery_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            received_at = record.get("received_at", "")
                            try:
                                record_time = datetime.fromisoformat(received_at)
                                if record_time >= cutoff:
                                    days_with_data.add(received_at[:10])
                                    feature_data.append(record)
                            except ValueError:
                                continue
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning("Failed to read delivery data: %s", e)

        if health_dir.exists():
            for client_dir in health_dir.iterdir():
                if not client_dir.is_dir():
                    continue
                health_file = client_dir / "health-history.jsonl"
                if not health_file.exists():
                    continue
                try:
                    with open(health_file) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                record = json.loads(line)
                                received_at = record.get("received_at", "")
                                try:
                                    record_time = datetime.fromisoformat(received_at)
                                    if record_time >= cutoff:
                                        days_with_data.add(received_at[:10])
                                        health_changes.append(record)
                                except ValueError:
                                    continue
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    continue

        days_collected = len(days_with_data)

        if days_collected < self.MIN_DAYS_FOR_COMPLETE:
            return self._insufficient_response(
                query_id=query_id,
                query_type="behavior_query",
                requesting_claw=requesting_claw,
                days_collected=days_collected,
                days_needed=self.MIN_DAYS_FOR_COMPLETE,
            )

        feature_adoption: dict[str, int] = {}
        health_by_client: dict[str, list[float]] = {}

        for record in feature_data:
            for feat in record.get("features", []):
                if isinstance(feat, str):
                    feature_adoption[feat] = feature_adoption.get(feat, 0) + 1

        for record in health_changes:
            client_id = record.get("client_id", "")
            score = record.get("health_score")
            if client_id and isinstance(score, (int, float)):
                if client_id not in health_by_client:
                    health_by_client[client_id] = []
                health_by_client[client_id].append(float(score))

        retention_correlation: list[dict[str, Any]] = []
        for client_id, scores in health_by_client.items():
            if len(scores) >= 2:
                delta = scores[-1] - scores[0]
                retention_correlation.append(
                    {
                        "client_id": client_id,
                        "health_delta": round(delta, 2),
                        "initial_score": scores[0],
                        "final_score": scores[-1],
                    }
                )

        return QueryResponse(
            query_id=str(hash(query_id) % 10000),
            query_type="behavior_query",
            responding_to=query_id,
            requesting_claw=requesting_claw,
            data_quality="complete",
            data={
                "feature_adoption_rates": feature_adoption,
                "retention_correlation": retention_correlation[:10],
                "lookback_days": lookback_days,
                "feature_filter": feature_id,
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=0,
            days_collected=days_collected,
            days_needed=self.MIN_DAYS_FOR_COMPLETE,
        )

    def _insufficient_response(
        self,
        query_id: str,
        query_type: str,
        requesting_claw: str,
        days_collected: int,
        days_needed: int,
    ) -> QueryResponse:
        """Return standard insufficient data response."""
        return QueryResponse(
            query_id=str(hash(query_id) % 10000),
            query_type=query_type,
            responding_to=query_id,
            requesting_claw=requesting_claw,
            data_quality="insufficient",
            data=None,
            generated_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=0,
            days_collected=days_collected,
            days_needed=days_needed,
        )

    def _count_days_collected(
        self,
        data_type: Literal[
            "content-performance", "client-health", "revenue", "delivery-velocity"
        ],
    ) -> int:
        """Count unique dates in a data directory."""
        dates: set[str] = set()
        data_dir = self.fs.get_data_path(data_type)

        if not data_dir.exists():
            return 0

        for jsonl_file in data_dir.rglob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            received_at = record.get("received_at", "")
                            if received_at:
                                dates.add(received_at[:10])
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue

        return len(dates)
