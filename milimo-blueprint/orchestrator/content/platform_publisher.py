# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for platform_publisher.

DEPRECATED: Import from milimo_core.content.platform_publisher directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.platform_publisher is deprecated; use milimo_core.content.platform_publisher instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.platform_publisher import *  # noqa: F403,F401
