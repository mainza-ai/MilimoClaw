# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for collection_workers.

DEPRECATED: Import from milimo_core.analytics.collection_workers directly.
"""

import warnings

warnings.warn(
    "orchestrator.analytics.collection_workers is deprecated; use milimo_core.analytics.collection_workers instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.analytics.collection_workers import *  # noqa: F403,F401
