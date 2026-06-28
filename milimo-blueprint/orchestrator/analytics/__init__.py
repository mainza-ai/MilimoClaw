# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for analytics claw modules.

DEPRECATED: Import from milimo_core.analytics directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics is deprecated; use milimo_core.analytics instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics import *  # noqa: F403,F401
