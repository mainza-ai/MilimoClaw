"""
Backward-compatibility shim for privacy_router module.

DEPRECATED: Import from milimo_core.privacy_router directly.
"""

import warnings

warnings.warn(
    "orchestrator.privacy_router is deprecated; use milimo_core.privacy_router instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.privacy_router import *  # noqa: F403,F401
