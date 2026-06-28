# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for doc_maintainer.

DEPRECATED: Import from milimo_core.build.doc_maintainer directly.
"""

import warnings

warnings.warn(
    "orchestrator.build.doc_maintainer is deprecated; use milimo_core.build.doc_maintainer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.build.doc_maintainer import *  # noqa: F403,F401
