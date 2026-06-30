# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for comms_manager.

DEPRECATED: Import from milimo_core.ops.comms_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.comms_manager is deprecated; use milimo_core.ops.comms_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.comms_manager import *  # noqa: F403,F401
