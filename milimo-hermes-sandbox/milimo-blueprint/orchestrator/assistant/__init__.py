# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for assistant claw modules.

DEPRECATED: Import from milimo_core.assistant directly.
"""

import warnings

warnings.warn(
    "orchestrator.assistant is deprecated; use milimo_core.assistant instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.assistant import *  # noqa: F403,F401
