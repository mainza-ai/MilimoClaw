# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Finance Claw Skill for Hermes."""

from milimo_hermes_plugin import register_finance_claw


def register(skill_registry):
    """Register finance claw skill."""
    register_finance_claw(skill_registry)


__all__ = ["register"]
