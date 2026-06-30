# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for brand_voice.

DEPRECATED: Import from milimo_core.content.brand_voice directly.
"""

import warnings

warnings.warn(
    "orchestrator.content.brand_voice is deprecated; use milimo_core.content.brand_voice instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.content.brand_voice import *  # noqa: F403,F401
