# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for dependency_auditor.

DEPRECATED: Import from milimo_core.build.dependency_auditor directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.dependency_auditor is deprecated; use milimo_core.build.dependency_auditor instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.dependency_auditor import *  # noqa: F403,F401
