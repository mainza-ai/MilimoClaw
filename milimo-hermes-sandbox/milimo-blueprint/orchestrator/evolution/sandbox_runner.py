# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for sandbox_runner.

DEPRECATED: Import from milimo_core.evolution directly.
"""

import warnings

warnings.warn(
    "orchestrator.evolution.sandbox_runner is deprecated; use milimo_core.evolution instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.evolution import *  # noqa: F403,F401
