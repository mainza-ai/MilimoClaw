# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for protocols modules.

DEPRECATED: Import from milimo_core.protocols directly.
"""

import warnings

warnings.warn(
    "orchestrator.protocols is deprecated; use milimo_core.protocols instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.protocols import *  # noqa: F403,F401
