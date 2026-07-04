# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for provenance_verifier module.

DEPRECATED: Import from milimo_core.provenance_verifier directly.
"""

import warnings

warnings.warn(
    "orchestrator.provenance_verifier is deprecated; use milimo_core.provenance_verifier instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.provenance_verifier import *  # noqa: F403,F401
