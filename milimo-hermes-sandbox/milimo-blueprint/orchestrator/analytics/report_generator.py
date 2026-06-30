# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for report_generator.

DEPRECATED: Import from milimo_core.analytics.report_generator directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.report_generator is deprecated; use milimo_core.analytics.report_generator instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.report_generator import *  # noqa: F403,F401
