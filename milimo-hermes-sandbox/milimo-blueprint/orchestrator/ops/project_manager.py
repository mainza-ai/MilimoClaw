# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for project_manager.

DEPRECATED: Import from milimo_core.ops.project_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.project_manager is deprecated; use milimo_core.ops.project_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.project_manager import *  # noqa: F403,F401
