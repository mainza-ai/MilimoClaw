# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for signal_processor.

DEPRECATED: Import from milimo_core.analytics.signal_processor directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.signal_processor is deprecated; use milimo_core.analytics.signal_processor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.signal_processor import *  # noqa: F403,F401
