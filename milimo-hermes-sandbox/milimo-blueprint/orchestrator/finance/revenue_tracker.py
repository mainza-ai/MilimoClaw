# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for revenue_tracker.

DEPRECATED: Import from milimo_core.finance.revenue_tracker directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.revenue_tracker is deprecated; use milimo_core.finance.revenue_tracker instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.revenue_tracker import *  # noqa: F403,F401
