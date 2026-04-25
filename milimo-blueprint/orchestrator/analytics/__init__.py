# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Analytics Claw Package

The intelligence layer of the Milimo Claw squad. Receives data signals
from all other claws, synthesizes them into actionable intelligence,
and publishes weekly reports consumed by the entire mesh.
"""

from .analytics_init import (
    AnalyticsFilesystemInit,
    AnalyticsLogEntry,
    AnalyticsOperationalLog,
    InitResult,
    ValidationResult,
    BASE,
    REQUIRED_DIRS,
    REQUIRED_FILES,
)
from .analytics_claw import AnalyticsClaw
from .analytics_scheduler import AnalyticsScheduler
from .anomaly_detector import AnomalyDetector, DetectedAnomaly
from .baseline_manager import (
    BaselineManager,
    ContentBaseline,
    RevenueBaseline,
    DeliveryBaseline,
)
from .forward_projector import ForwardProjector, ForwardProjection
from .opportunity_scorer import OpportunityScorer, ScoredOpportunity
from .query_handler import QueryHandler, QueryResponse
from .report_generator import ReportGenerator, WeeklyReport
from .signal_dispatcher import SignalDispatcher
from .signal_processor import SignalProcessor

__all__ = [
    "AnalyticsFilesystemInit",
    "AnalyticsLogEntry",
    "AnalyticsOperationalLog",
    "InitResult",
    "ValidationResult",
    "BASE",
    "REQUIRED_DIRS",
    "REQUIRED_FILES",
    "AnalyticsClaw",
    "AnalyticsScheduler",
    "AnomalyDetector",
    "DetectedAnomaly",
    "BaselineManager",
    "ContentBaseline",
    "RevenueBaseline",
    "DeliveryBaseline",
    "ForwardProjector",
    "ForwardProjection",
    "OpportunityScorer",
    "ScoredOpportunity",
    "QueryHandler",
    "QueryResponse",
    "ReportGenerator",
    "WeeklyReport",
    "SignalDispatcher",
    "SignalProcessor",
]
