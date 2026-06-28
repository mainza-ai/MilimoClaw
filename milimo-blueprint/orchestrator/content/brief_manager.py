# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for brief_manager.

DEPRECATED: Import from milimo_core.content.brief_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.brief_manager is deprecated; use milimo_core.content.brief_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.brief_manager import *  # noqa: F403,F401
