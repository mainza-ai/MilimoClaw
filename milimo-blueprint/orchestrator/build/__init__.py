# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for build claw modules.

DEPRECATED: Import from milimo_core.build directly.
"""

import warnings

warnings.warn(
    "orchestrator.build is deprecated; use milimo_core.build instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build import *  # noqa: F403,F401
