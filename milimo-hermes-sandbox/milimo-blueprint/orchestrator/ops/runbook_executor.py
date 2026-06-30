# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for runbook_executor.

DEPRECATED: Import from milimo_core.ops.runbook_executor directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.runbook_executor is deprecated; use milimo_core.ops.runbook_executor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.runbook_executor import *  # noqa: F403,F401
