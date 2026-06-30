# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for content_init.

DEPRECATED: Import from milimo_core.content.content_init directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.content_init is deprecated; use milimo_core.content.content_init instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.content_init import *  # noqa: F403,F401
