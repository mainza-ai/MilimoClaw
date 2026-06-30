# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for provenance_signer module.

DEPRECATED: Import from milimo_core.provenance_signer directly.
"""

import warnings

warnings.warn(
    "orchestrator.provenance_signer is deprecated; use milimo_core.provenance_signer instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.provenance_signer import *  # noqa: F403,F401
