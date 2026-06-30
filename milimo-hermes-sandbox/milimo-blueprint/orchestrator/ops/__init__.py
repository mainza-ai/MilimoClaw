# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for ops claw modules.

DEPRECATED: Import from milimo_core.ops directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops is deprecated; use milimo_core.ops instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops import *  # noqa: F403,F401
