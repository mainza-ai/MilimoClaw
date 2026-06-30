# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for forward_projector.

DEPRECATED: Import from milimo_core.analytics.forward_projector directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.forward_projector is deprecated; use milimo_core.analytics.forward_projector instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.forward_projector import *  # noqa: F403,F401
