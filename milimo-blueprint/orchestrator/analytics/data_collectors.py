# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for data_collectors.

DEPRECATED: Import from milimo_core.analytics.data_collectors directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.data_collectors is deprecated; use milimo_core.analytics.data_collectors instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.data_collectors import *  # noqa: F403,F401
