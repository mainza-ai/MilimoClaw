# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for scope_monitor.

DEPRECATED: Import from milimo_core.ops.scope_monitor directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.scope_monitor is deprecated; use milimo_core.ops.scope_monitor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.scope_monitor import *  # noqa: F403,F401
