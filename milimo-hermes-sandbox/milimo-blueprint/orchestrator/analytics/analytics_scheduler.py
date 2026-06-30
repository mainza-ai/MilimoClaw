# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for analytics_scheduler.

DEPRECATED: Import from milimo_core.analytics.analytics_scheduler directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.analytics_scheduler is deprecated; use milimo_core.analytics.analytics_scheduler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.analytics_scheduler import *  # noqa: F403,F401
