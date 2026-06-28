# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Analytics Claw Skill for Hermes."""

from milimo_hermes_plugin import register_analytics_claw


def register(skill_registry):
    """Register analytics claw skill."""
    register_analytics_claw(skill_registry)


__all__ = ["register"]
