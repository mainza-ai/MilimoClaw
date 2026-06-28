# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for contracts module.

DEPRECATED: Import from milimo_core.contracts directly.
"""

import warnings

warnings.warn(
    "orchestrator.contracts is deprecated; use milimo_core.contracts instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.contracts import *  # noqa: F403,F401
