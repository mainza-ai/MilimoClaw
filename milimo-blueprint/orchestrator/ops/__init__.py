# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Ops Claw — Main Package

The account manager and project manager of the Milimo Claw mesh.
Handles the full client lifecycle — from inquiry to delivery and invoice.
"""

from .ops_init import (
    OpsFilesystemInit,
    OpsOperationalLog,
    OpsCommsLog,
    OpsLogEntry,
    CommsLogEntry,
    InitResult,
    ValidationResult,
    BASE,
    REQUIRED_DIRS,
    REQUIRED_TEMPLATE_FILES,
    REQUIRED_LOG_FILES,
)
from .signal_dispatcher import (
    OpsSignalDispatcher,
    PricingNotConfirmedError,
)
from .approval_handler import (
    OpsApprovalHandler,
    OpsApprovalAction,
)
from .intake_manager import (
    IntakeManager,
    TriageScore,
    ClientBrief,
)
from .health_scorer import (
    ClientHealthScorer,
    ClientHealthScore,
)
from .project_manager import (
    ProjectManager,
    ProjectStatus,
    DeadlineRisk,
)
from .scope_monitor import (
    ScopeMonitor,
    ScopeCreepDetection,
)
from .comms_manager import (
    CommsManager,
    ClientMessage,
)
from .ops_scheduler import OpsScheduler
from .ops_claw import (
    OpsClaw,
    MockMeshGateway,
)

__all__ = [
    "OpsFilesystemInit",
    "OpsOperationalLog",
    "OpsCommsLog",
    "OpsLogEntry",
    "CommsLogEntry",
    "InitResult",
    "ValidationResult",
    "BASE",
    "REQUIRED_DIRS",
    "REQUIRED_TEMPLATE_FILES",
    "REQUIRED_LOG_FILES",
    "OpsSignalDispatcher",
    "PricingNotConfirmedError",
    "OpsApprovalHandler",
    "OpsApprovalAction",
    "IntakeManager",
    "TriageScore",
    "ClientBrief",
    "ClientHealthScorer",
    "ClientHealthScore",
    "ProjectManager",
    "ProjectStatus",
    "DeadlineRisk",
    "ScopeMonitor",
    "ScopeCreepDetection",
    "CommsManager",
    "ClientMessage",
    "OpsScheduler",
    "OpsClaw",
    "MockMeshGateway",
]
