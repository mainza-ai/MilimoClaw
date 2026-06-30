"""Conftest for Hermes plugin integration tests."""

import pytest
import sys
from pathlib import Path

# Ensure milimo-core is on path
milimo_core_path = Path(__file__).parent.parent.parent / "milimo-core" / "src"
sys.path.insert(0, str(milimo_core_path))

# Ensure milimo-hermes-plugin is on path
plugin_path = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_path))


@pytest.fixture(autouse=True)
def cleanup_global_state():
    """Clean up global state before and after each test."""
    import milimo_hermes_plugin.tools as tools_module

    # Save original state
    original_launcher = tools_module._claw_launcher
    original_handler = tools_module._approval_handler
    original_cost_guard = tools_module._cost_guard
    original_notifier = tools_module._warroom_notifier

    yield

    # Restore
    tools_module._claw_launcher = original_launcher
    tools_module._approval_handler = original_handler
    tools_module._cost_guard = original_cost_guard
    tools_module._warroom_notifier = original_notifier
