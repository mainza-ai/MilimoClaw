# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for stub_vercel.

DEPRECATED: Import from milimo_core.stubs.stub_vercel directly.
"""

import warnings

warnings.warn(
    "orchestrator.stubs.stub_vercel is deprecated; use milimo_core.stubs.stub_vercel instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.stubs.stub_vercel import *  # noqa: F403,F401
