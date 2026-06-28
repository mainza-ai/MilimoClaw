# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for issue_manager.

DEPRECATED: Import from milimo_core.build.issue_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.issue_manager is deprecated; use milimo_core.build.issue_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.issue_manager import *  # noqa: F403,F401
