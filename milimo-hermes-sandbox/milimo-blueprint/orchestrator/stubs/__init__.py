# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stubs modules.

DEPRECATED: Import from milimo_core.stubs directly.
"""

import warnings

warnings.warn(
    "orchestrator.stubs is deprecated; use milimo_core.stubs instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.stubs import *  # noqa: F403,F401
