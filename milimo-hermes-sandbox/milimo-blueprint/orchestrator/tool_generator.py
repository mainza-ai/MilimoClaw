# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for tool_generator module.

DEPRECATED: Import from milimo_core.tool_generator directly.
"""

import warnings

warnings.warn(
    "orchestrator.tool_generator is deprecated; use milimo_core.tool_generator instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.tool_generator import *  # noqa: F403,F401
