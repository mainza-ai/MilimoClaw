# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for build_scheduler.

DEPRECATED: Import from milimo_core.build.build_scheduler directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.build_scheduler is deprecated; use milimo_core.build.build_scheduler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.build_scheduler import *  # noqa: F403,F401
