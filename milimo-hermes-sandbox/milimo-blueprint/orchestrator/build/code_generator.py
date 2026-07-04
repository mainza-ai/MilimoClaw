# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for code_generator.

DEPRECATED: Import from milimo_core.build.code_generator directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.code_generator is deprecated; use milimo_core.build.code_generator instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.code_generator import *  # noqa: F403,F401
