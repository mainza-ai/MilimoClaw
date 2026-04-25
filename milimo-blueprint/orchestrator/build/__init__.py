# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Build Claw — Engineering automation for MilimoClaw.

Handles GitHub issues, sprint planning, code generation, PR management,
deployments, error monitoring, cost tracking, dependency auditing,
and documentation maintenance.

13 modules:
- build_init: Filesystem initialization and operational logging
- signal_dispatcher: Inter-claw communication
- approval_handler: Two-stage REVIEW → HOLD approval flow
- issue_manager: Sprint planning, velocity tracking, backlog scoring
- code_generator: Code generation with hash-anchored edits
- pr_manager: PR lifecycle management
- deploy_manager: Deployment management with separate HOLD
- error_monitor: Error pattern detection and monitoring
- cost_monitor: Inference cost tracking and baseline
- dependency_auditor: Security vulnerability scanning
- doc_maintainer: Changelog, devlog, API documentation
- build_scheduler: Periodic task scheduling
- build_claw: Main entry point
"""

from .build_init import (
    BASE,
    REQUIRED_DIRS,
    REQUIRED_FILES,
    INFERENCE_FALLBACK_CHAIN,
    BUILD_CATEGORIES,
    BuildFilesystemInit,
    BuildLogEntry,
    BuildOperationalLog,
    InitResult,
    ValidationResult,
)
from .build_claw import BuildClaw
from .build_scheduler import (
    BuildScheduler,
    ERROR_MONITOR_INTERVAL,
    COST_MONITOR_INTERVAL,
    DEPENDENCY_AUDIT_INTERVAL,
)
from .signal_dispatcher import (
    BuildSignalDispatcher,
    PendingBehaviorQuery,
    ANALYTICS_WAIT_SECONDS,
)
from .approval_handler import (
    BuildApprovalHandler,
    BuildApprovalAction,
    ApprovalResult,
    PRActivityLog,
    DeployActivityLog,
)

__all__ = [
    "BASE",
    "REQUIRED_DIRS",
    "REQUIRED_FILES",
    "INFERENCE_FALLBACK_CHAIN",
    "BUILD_CATEGORIES",
    "BuildFilesystemInit",
    "BuildLogEntry",
    "BuildOperationalLog",
    "InitResult",
    "ValidationResult",
    "BuildClaw",
    "BuildScheduler",
    "ERROR_MONITOR_INTERVAL",
    "COST_MONITOR_INTERVAL",
    "DEPENDENCY_AUDIT_INTERVAL",
    "BuildSignalDispatcher",
    "PendingBehaviorQuery",
    "ANALYTICS_WAIT_SECONDS",
    "BuildApprovalHandler",
    "BuildApprovalAction",
    "ApprovalResult",
    "PRActivityLog",
    "DeployActivityLog",
]
