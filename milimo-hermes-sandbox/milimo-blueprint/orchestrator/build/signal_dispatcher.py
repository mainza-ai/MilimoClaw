# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for signal_dispatcher.

DEPRECATED: Import from milimo_core.build.signal_dispatcher directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.signal_dispatcher is deprecated; use milimo_core.build.signal_dispatcher instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.signal_dispatcher import *  # noqa: F403,F401
