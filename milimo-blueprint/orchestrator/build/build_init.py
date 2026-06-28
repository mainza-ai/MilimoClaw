# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for build_init.

DEPRECATED: Import from milimo_core.build.build_init directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.build_init is deprecated; use milimo_core.build.build_init instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.build_init import *  # noqa: F403,F401
