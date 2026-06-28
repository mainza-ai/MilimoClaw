# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for payment_risk_scorer.

DEPRECATED: Import from milimo_core.finance.payment_risk_scorer directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.payment_risk_scorer is deprecated; use milimo_core.finance.payment_risk_scorer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.payment_risk_scorer import *  # noqa: F403,F401
