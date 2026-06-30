# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for pricing_engine.

DEPRECATED: Import from milimo_core.finance.pricing_engine directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.pricing_engine is deprecated; use milimo_core.finance.pricing_engine instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.pricing_engine import *  # noqa: F403,F401
