# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Service protocols for external integrations."""

from .github_protocol import GitHubClientProtocol
from .deploy_protocol import DeployClientProtocol
from .monitoring_protocol import MonitoringClientProtocol
from .payments_protocol import PaymentsClientProtocol
from .delegation import ClawTask, ClawResult, DelegationAdapter
from .scheduling import ScheduledJob, SchedulerInterface

__all__ = [
    "GitHubClientProtocol",
    "DeployClientProtocol",
    "MonitoringClientProtocol",
    "PaymentsClientProtocol",
    "ClawTask",
    "ClawResult",
    "DelegationAdapter",
    "ScheduledJob",
    "SchedulerInterface",
]
