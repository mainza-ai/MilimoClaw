# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stub_github.

DEPRECATED: Import from milimo_core.stubs.stub_github directly.
"""

import warnings

warnings.warn(
    "orchestrator.stubs.stub_github is deprecated; use milimo_core.stubs.stub_github instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.stubs.stub_github import *  # noqa: F403,F401
