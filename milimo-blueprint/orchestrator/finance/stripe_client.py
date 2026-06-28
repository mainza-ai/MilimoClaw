# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stripe_client.

DEPRECATED: Import from milimo_core.finance.stripe_client directly.
"""

import warnings

warnings.warn(
    "orchestrator.finance.stripe_client is deprecated; use milimo_core.finance.stripe_client instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.finance.stripe_client import *  # noqa: F403,F401
