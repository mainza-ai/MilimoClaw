# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for sentry_client.

DEPRECATED: Import from milimo_core.build.sentry_client directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.sentry_client is deprecated; use milimo_core.build.sentry_client instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.sentry_client import *  # noqa: F403,F401
