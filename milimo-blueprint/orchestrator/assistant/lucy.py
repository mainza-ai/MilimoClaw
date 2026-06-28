# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for lucy.

DEPRECATED: Import from milimo_core.assistant.lucy directly.
"""

import warnings

warnings.warn(
    "orchestrator.assistant.lucy is deprecated; use milimo_core.assistant.lucy instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.assistant.lucy import *  # noqa: F403,F401
