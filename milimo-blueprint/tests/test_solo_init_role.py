#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for get_claws_to_initialize in solo_init.py."""

from __future__ import annotations

import pytest


def test_import():
    """Test that we can import the function."""
    from orchestrator.solo_init import get_claws_to_initialize

    assert callable(get_claws_to_initialize)


def test_solo_mode_returns_all_active_claws():
    """Solo mode should return all active claws from the template."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "solo",
        "activeClaws": ["content", "ops", "analytics", "finance", "build"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["content", "ops", "analytics", "finance", "build"]


def test_solo_mode_respects_template_active_claws():
    """content-agency only has 3 claws — solo mode should init only those 3."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "solo",
        "activeClaws": ["content", "ops", "analytics"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["content", "ops", "analytics"]
    assert "finance" not in result
    assert "build" not in result


def test_solo_mode_for_ai_micro_saas():
    """ai-micro-saas has 4 claws including build."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "solo",
        "activeClaws": ["build", "ops", "analytics", "finance"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["build", "ops", "analytics", "finance"]
    assert "content" not in result


def test_mesh_mode_returns_single_claw():
    """Mesh mode should return only the one claw this operator runs."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "analytics",
        "activeClaws": ["content", "ops", "analytics", "finance", "build"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["analytics"]


def test_mesh_mode_role_not_in_active_claws_raises():
    """Mesh mode with role not in template should raise ValueError."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "build",
        "activeClaws": ["content", "ops", "analytics"],  # build not in template
    }
    with pytest.raises(ValueError, match="not in activeClaws"):
        get_claws_to_initialize(config)


def test_defaults_to_all_claws_when_role_missing():
    """Missing clawRole should default to solo mode with all claws."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {}  # no clawRole key
    result = get_claws_to_initialize(config)
    assert len(result) == 5
    assert result == ["content", "ops", "analytics", "finance", "build"]


def test_defaults_to_all_claws_when_role_is_solo_and_active_claws_missing():
    """Solo mode without activeClaws should default to all claws."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {"clawRole": "solo"}  # no activeClaws key
    result = get_claws_to_initialize(config)
    assert len(result) == 5


def test_mesh_mode_with_content_role():
    """Mesh mode with content role."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "content",
        "activeClaws": ["content", "ops", "analytics"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["content"]


def test_mesh_mode_with_finance_role():
    """Mesh mode with finance role."""
    from orchestrator.solo_init import get_claws_to_initialize

    config = {
        "clawRole": "finance",
        "activeClaws": ["ops", "analytics", "finance"],
    }
    result = get_claws_to_initialize(config)
    assert result == ["finance"]


def test_detect_filesystem_config_respects_claws_to_init():
    """detect_filesystem_config should only create paths for specified claws."""
    from orchestrator.solo_init import detect_filesystem_config

    # Request only 3 claws
    fs_config = detect_filesystem_config("test-squad", claws_to_init=["content", "ops", "analytics"])

    assert len(fs_config.claw_paths) == 3
    assert "content" in fs_config.claw_paths
    assert "ops" in fs_config.claw_paths
    assert "analytics" in fs_config.claw_paths
    assert "finance" not in fs_config.claw_paths
    assert "build" not in fs_config.claw_paths


def test_detect_filesystem_config_defaults_to_all_claws():
    """detect_filesystem_config without claws_to_init should create all claws."""
    from orchestrator.solo_init import detect_filesystem_config

    fs_config = detect_filesystem_config("test-squad")

    assert len(fs_config.claw_paths) == 5
    assert "content" in fs_config.claw_paths
    assert "ops" in fs_config.claw_paths
    assert "analytics" in fs_config.claw_paths
    assert "finance" in fs_config.claw_paths
    assert "build" in fs_config.claw_paths
