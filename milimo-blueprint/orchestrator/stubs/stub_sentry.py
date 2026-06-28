# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stub_sentry.

DEPRECATED: Import from milimo_core.stubs.stub_sentry directly.
"""

import warnings

warnings.warn(
    "orchestrator.stubs.stub_sentry is deprecated; use milimo_core.stubs.stub_sentry instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.stubs.stub_sentry import *  # noqa: F403,F401
