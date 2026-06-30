# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for incident_analyzer.

DEPRECATED: Import from milimo_core.ops.incident_analyzer directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.incident_analyzer is deprecated; use milimo_core.ops.incident_analyzer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.incident_analyzer import *  # noqa: F403,F401
