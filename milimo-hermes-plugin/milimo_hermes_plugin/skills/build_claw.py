# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Build Claw Skill for Hermes."""

from milimo_hermes_plugin import register_build_claw


def register(skill_registry):
    """Register build claw skill."""
    register_build_claw(skill_registry)


__all__ = ["register"]
