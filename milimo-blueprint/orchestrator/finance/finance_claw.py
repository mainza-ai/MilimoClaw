# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for finance_claw.

DEPRECATED: Import from milimo_core.finance.finance_claw directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.finance_claw is deprecated; use milimo_core.finance.finance_claw instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.finance_claw import *  # noqa: F403,F401
