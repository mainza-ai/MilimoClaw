# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for payment_monitor.

DEPRECATED: Import from milimo_core.finance.payment_monitor directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.payment_monitor is deprecated; use milimo_core.finance.payment_monitor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.payment_monitor import *  # noqa: F403,F401
