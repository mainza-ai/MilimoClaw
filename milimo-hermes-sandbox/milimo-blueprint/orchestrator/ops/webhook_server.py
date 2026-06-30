# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for webhook_server.

DEPRECATED: Import from milimo_core.ops.webhook_server directly.
"""

import warnings

warnings.warn(
    "orchestrator.ops.webhook_server is deprecated; use milimo_core.ops.webhook_server instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.ops.webhook_server import *  # noqa: F403,F401
