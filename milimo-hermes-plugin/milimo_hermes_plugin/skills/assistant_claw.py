# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Assistant Claw Skill for Hermes."""

from milimo_hermes_plugin import register_assistant_claw


def register(skill_registry):
    """Register assistant claw skill."""
    register_assistant_claw(skill_registry)


__all__ = ["register"]
