# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for tool_validator module.

DEPRECATED: Import from milimo_core.tool_validator directly.
"""

import warnings

warnings.warn(
    "orchestrator.tool_validator is deprecated; use milimo_core.tool_validator instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.tool_validator import *  # noqa: F403,F401
