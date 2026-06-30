# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Analytics Claw modules - Intelligence layer."""

from .analytics_claw import AnalyticsClaw
from .analytics_init import AnalyticsFilesystemInit, AnalyticsOperationalLog, AnalyticsLogEntry
from .analytics_scheduler import AnalyticsScheduler
from .signal_processor import SignalProcessor
from .signal_dispatcher import SignalDispatcher
from .anomaly_detector import AnomalyDetector, DetectedAnomaly
from .opportunity_scorer import OpportunityScorer, ScoredOpportunity
from .report_generator import ReportGenerator, WeeklyReport
from .baseline_manager import BaselineManager, ContentBaseline, RevenueBaseline, DeliveryBaseline
from .query_handler import QueryHandler, QueryResponse
from .forward_projector import ForwardProjector, ForwardProjection
from .collection_workers import CollectionWorker

__all__ = [
    "AnalyticsClaw",
    "AnalyticsFilesystemInit",
    "AnalyticsOperationalLog",
    "AnalyticsLogEntry",
    "AnalyticsScheduler",
    "SignalProcessor",
    "SignalDispatcher",
    "AnomalyDetector",
    "DetectedAnomaly",
    "OpportunityScorer",
    "ScoredOpportunity",
    "ReportGenerator",
    "WeeklyReport",
    "BaselineManager",
    "ContentBaseline",
    "RevenueBaseline",
    "DeliveryBaseline",
    "QueryHandler",
    "QueryResponse",
    "ForwardProjector",
    "ForwardProjection",
    "CollectionWorker",
]
