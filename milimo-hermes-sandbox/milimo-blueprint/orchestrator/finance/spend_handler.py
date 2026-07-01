# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for spend_handler.

DEPRECATED: Import from milimo_core.finance.spend_handler directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.spend_handler is deprecated; use milimo_core.finance.spend_handler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.spend_handler import *  # noqa: F403,F401
