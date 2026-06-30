# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for monitoring_protocol.

DEPRECATED: Import from milimo_core.protocols.monitoring_protocol directly.
"""

import warnings

warnings.warn(
    "orchestrator.protocols.monitoring_protocol is deprecated; use milimo_core.protocols.monitoring_protocol instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.protocols.monitoring_protocol import *  # noqa: F403,F401
