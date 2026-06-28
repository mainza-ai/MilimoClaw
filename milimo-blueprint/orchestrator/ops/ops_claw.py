# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for ops_claw.

DEPRECATED: Import from milimo_core.ops.ops_claw directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.ops_claw is deprecated; use milimo_core.ops.ops_claw instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.ops_claw import *  # noqa: F403,F401
