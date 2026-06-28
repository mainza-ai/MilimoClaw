# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for cost_monitor.

DEPRECATED: Import from milimo_core.build.cost_monitor directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.cost_monitor is deprecated; use milimo_core.build.cost_monitor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.cost_monitor import *  # noqa: F403,F401
