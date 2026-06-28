# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for content_scheduler.

DEPRECATED: Import from milimo_core.content.content_scheduler directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.content_scheduler is deprecated; use milimo_core.content.content_scheduler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.content_scheduler import *  # noqa: F403,F401
