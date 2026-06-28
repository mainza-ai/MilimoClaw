# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Content Claw Skill for Hermes."""

from milimo_hermes_plugin import register_content_claw


def register(skill_registry):
    """Register content claw skill."""
    register_content_claw(skill_registry)


__all__ = ["register"]
