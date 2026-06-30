# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for analytics_init.

DEPRECATED: Import from milimo_core.analytics.analytics_init directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.analytics_init is deprecated; use milimo_core.analytics.analytics_init instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.analytics_init import *  # noqa: F403,F401
