# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Ops Claw Skill for Hermes."""

from milimo_hermes_plugin import register_ops_claw


def register(skill_registry):
    """Register ops claw skill."""
    register_ops_claw(skill_registry)


__all__ = ["register"]
