# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for analytics_claw.

DEPRECATED: Import from milimo_core.analytics.analytics_claw directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.analytics_claw is deprecated; use milimo_core.analytics.analytics_claw instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.analytics_claw import *  # noqa: F403,F401
