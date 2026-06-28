# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for finance_scheduler.

DEPRECATED: Import from milimo_core.finance.finance_scheduler directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.finance_scheduler is deprecated; use milimo_core.finance.finance_scheduler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.finance_scheduler import *  # noqa: F403,F401
