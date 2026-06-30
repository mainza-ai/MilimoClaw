# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for intake_manager.

DEPRECATED: Import from milimo_core.ops.intake_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.intake_manager is deprecated; use milimo_core.ops.intake_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.intake_manager import *  # noqa: F403,F401
