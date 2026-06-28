# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for deploy_manager.

DEPRECATED: Import from milimo_core.build.deploy_manager directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.deploy_manager is deprecated; use milimo_core.build.deploy_manager instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.deploy_manager import *  # noqa: F403,F401
