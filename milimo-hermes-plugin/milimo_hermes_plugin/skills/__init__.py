# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Milimo Hermes Plugin Skills Package.

This package contains all 6 claw handler skills plus the shared milimo-core-primitives handler.
"""

from .build_claw import register as register_build_claw
from .content_claw import register as register_content_claw
from .ops_claw import register as register_ops_claw
from .analytics_claw import register as register_analytics_claw
from .finance_claw import register as register_finance_claw
from .assistant_claw import register as register_assistant_claw
from .milimo_core_primitives import register as register_milimo_core_primitives


def register_all_skills(skill_registry):
    """Register all Milimo claw handler skills with the skill registry."""
    register_milimo_core_primitives(skill_registry)
    register_build_claw(skill_registry)
    register_content_claw(skill_registry)
    register_ops_claw(skill_registry)
    register_analytics_claw(skill_registry)
    register_finance_claw(skill_registry)
    register_assistant_claw(skill_registry)


__all__ = [
    "register_all_skills",
    "register_build_claw",
    "register_content_claw",
    "register_ops_claw",
    "register_analytics_claw",
    "register_finance_claw",
    "register_assistant_claw",
    "register_milimo_core_primitives",
]
