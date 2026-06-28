# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for milimo_paths module.

DEPRECATED: Import from milimo_core.milimo_paths directly.
"""

import warnings

warnings.warn(
    "orchestrator.milimo_paths is deprecated; use milimo_core.milimo_paths instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.milimo_paths import *  # noqa: F403,F401
