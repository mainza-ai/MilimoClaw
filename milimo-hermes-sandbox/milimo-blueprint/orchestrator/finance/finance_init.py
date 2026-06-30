# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for finance_init.

DEPRECATED: Import from milimo_core.finance.finance_init directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.finance_init is deprecated; use milimo_core.finance.finance_init instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.finance_init import *  # noqa: F403,F401
