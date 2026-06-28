# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for health_scorer.

DEPRECATED: Import from milimo_core.ops.health_scorer directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.health_scorer is deprecated; use milimo_core.ops.health_scorer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.health_scorer import *  # noqa: F403,F401
