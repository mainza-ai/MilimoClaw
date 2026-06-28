# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for vercel_client.

DEPRECATED: Import from milimo_core.build.vercel_client directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.vercel_client is deprecated; use milimo_core.build.vercel_client instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.vercel_client import *  # noqa: F403,F401
