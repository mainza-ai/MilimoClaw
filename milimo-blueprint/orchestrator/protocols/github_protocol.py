# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for github_protocol.

DEPRECATED: Import from milimo_core.protocols.github_protocol directly.
"""

import warnings

warnings.warn(
    "orchestrator.protocols.github_protocol is deprecated; use milimo_core.protocols.github_protocol instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.protocols.github_protocol import *  # noqa: F403,F401
