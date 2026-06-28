# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for query_handler.

DEPRECATED: Import from milimo_core.analytics.query_handler directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.query_handler is deprecated; use milimo_core.analytics.query_handler instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.query_handler import *  # noqa: F403,F401
