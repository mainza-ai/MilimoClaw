# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for tool_sandbox module.

DEPRECATED: Import from milimo_core.tool_sandbox directly.
"""

import warnings

warnings.warn(
    "orchestrator.tool_sandbox is deprecated; use milimo_core.tool_sandbox instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.tool_sandbox import *  # noqa: F403,F401
