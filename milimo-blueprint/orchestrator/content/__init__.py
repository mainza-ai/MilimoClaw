# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for content claw modules.

DEPRECATED: Import from milimo_core.content directly.
"""

import warnings

warnings.warn(
    "orchestrator.content is deprecated; use milimo_core.content instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content import *  # noqa: F403,F401
