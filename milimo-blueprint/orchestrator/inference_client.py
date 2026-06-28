"""
Backward-compatibility shim for inference_client module.

DEPRECATED: Import from milimo_core.inference_client directly.
"""

import warnings

warnings.warn(
    "orchestrator.inference_client is deprecated; use milimo_core.inference_client instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.inference_client import *  # noqa: F403,F401
