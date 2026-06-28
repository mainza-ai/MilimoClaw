# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for approval_handler.

DEPRECATED: Import from milimo_core.content.approval_handler directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.approval_handler is deprecated; use milimo_core.content.approval_handler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.approval_handler import *  # noqa: F403,F401
