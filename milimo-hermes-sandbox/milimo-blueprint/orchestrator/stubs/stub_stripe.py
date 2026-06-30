# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stub_stripe.

DEPRECATED: Import from milimo_core.stubs.stub_stripe directly.
"""

import warnings

warnings.warn(
    "orchestrator.stubs.stub_stripe is deprecated; use milimo_core.stubs.stub_stripe instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.stubs.stub_stripe import *  # noqa: F403,F401
