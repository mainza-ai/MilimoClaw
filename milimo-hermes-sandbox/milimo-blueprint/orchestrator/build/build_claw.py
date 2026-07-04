# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for build_claw.

DEPRECATED: Import from milimo_core.build.build_claw directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.build_claw is deprecated; use milimo_core.build.build_claw instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.build_claw import *  # noqa: F403,F401
