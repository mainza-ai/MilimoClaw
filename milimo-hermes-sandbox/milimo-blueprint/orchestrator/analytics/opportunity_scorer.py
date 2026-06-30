# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for opportunity_scorer.

DEPRECATED: Import from milimo_core.analytics.opportunity_scorer directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.opportunity_scorer is deprecated; use milimo_core.analytics.opportunity_scorer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.opportunity_scorer import *  # noqa: F403,F401
