# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for finance claw modules.

DEPRECATED: Import from milimo_core.finance directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance is deprecated; use milimo_core.finance instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance import *  # noqa: F403,F401
