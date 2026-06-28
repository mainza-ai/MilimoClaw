# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for service_factory module.

DEPRECATED: Import from milimo_core.service_factory directly.
"""

import warnings

warnings.warn(
    "orchestrator.service_factory is deprecated; use milimo_core.service_factory instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.service_factory import *  # noqa: F403,F401
