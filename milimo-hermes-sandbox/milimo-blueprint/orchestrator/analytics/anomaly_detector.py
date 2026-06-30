# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for anomaly_detector.

DEPRECATED: Import from milimo_core.analytics.anomaly_detector directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.anomaly_detector is deprecated; use milimo_core.analytics.anomaly_detector instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.anomaly_detector import *  # noqa: F403,F401
