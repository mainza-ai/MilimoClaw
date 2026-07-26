"""Tests for Hermes plugin tool registration.

These tests verify the plugin registers its tools correctly with the
Hermes Agent runtime.  The most common production failure is a mismatch
between the toolset name used in register_core_tools() and the toolset
name declared in the Hermes config's platform_toolsets.api_server.
"""

import json
import sys
from pathlib import Path

import pytest

# ── Helpers ────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
_PLUGIN_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _PLUGIN_DIR.parent
_SANDBOX_DIR = _PROJECT_ROOT / "milimo-hermes-sandbox"


def _get_toolset_from_config() -> str | None:
    """Parse the toolset name from generate-config.ts."""
    config_path = _SANDBOX_DIR / "generate-config.ts"
    if not config_path.exists():
        config_path = _PROJECT_ROOT / "milimo-hermes-sandbox" / "generate-config.ts"
    text = config_path.read_text()

    # API_SERVER_TOOLSETS is an array of strings.  Find the entry that
    # starts with "milimo" to get the canonical Milimo toolset name.
    # This is fragile but better than having no cross-reference at all.
    import re
    # Match: "milimo-hermes", (with trailing comma or bracket)
    match = re.search(r'"milimo[^"]*"', text)
    if match:
        return match.group(0).strip('"')
    return None


# ── Toolset name consistency ───────────────────────────────────────────────

TOOLSET_NAME = "milimo-hermes"


def test_toolset_name_matches_config():
    """register_core_tools uses the same toolset name as generate-config.ts.

    If they diverge, the tools are registered but invisible to every
    Hermes session because the API server only exposes tools whose
    toolset matches its platform_toolsets.api_server list.
    """
    from milimo_hermes_plugin.tools import register_core_tools

    # Check the source code of register_core_tools for the toolset arg
    import inspect
    source = inspect.getsource(register_core_tools)
    assert f'toolset="{TOOLSET_NAME}"' in source, (
        f"register_core_tools uses toolset={TOOLSET_NAME!r} but "
        f"the source contains a different value.\n"
        f"Expected: toolset=\"{TOOLSET_NAME}\"\n"
        f"Source excerpt:\n{source}"
    )


def test_toolset_name_in_config():
    """generate-config.ts includes the Milimo toolset name."""
    toolset = _get_toolset_from_config()
    assert toolset == TOOLSET_NAME, (
        f"generate-config.ts declares toolset {toolset!r} "
        f"but tests expect {TOOLSET_NAME!r}"
    )


def test_toolset_name_in_genesis_yaml():
    """The generated config.yaml would include the Milimo toolset."""
    # We cannot read the actual config.yaml (it lives inside the
    # sandbox container), but we can verify that the generation code
    # would produce the right value by inspecting generate-config.ts.
    toolset = _get_toolset_from_config()
    assert toolset is not None, "Could not extract toolset from generate-config.ts"


# ── Core tools integrity ───────────────────────────────────────────────────

CORE_TOOL_NAMES = [
    "milimo_status",
    "milimo_warroom",
    "milimo_approve",
    "milimo_veto",
    "milimo_spend",
    "delegate_task",
]

CORE_TOOL_REQUIRED_SCHEMA_KEYS = [
    "name",
    "description",
    "parameters",
]


def test_core_tools_count():
    """Exactly 6 core tools are defined."""
    from milimo_hermes_plugin.tools import _CORE_TOOLS
    assert len(_CORE_TOOLS) == len(CORE_TOOL_NAMES), (
        f"Expected {len(CORE_TOOL_NAMES)} core tools, "
        f"got {len(_CORE_TOOLS)}"
    )


def test_core_tools_names():
    """All expected core tools are present."""
    from milimo_hermes_plugin.tools import _CORE_TOOLS
    registered = {t[0] for t in _CORE_TOOLS}
    expected = set(CORE_TOOL_NAMES)
    missing = expected - registered
    extra = registered - expected
    assert not missing, f"Missing core tools: {missing}"
    assert not extra, f"Unexpected core tools: {extra}"


def test_core_tools_schemas():
    """Each core tool has a valid schema with required keys."""
    from milimo_hermes_plugin.tools import _CORE_TOOLS
    for name, schema, handler in _CORE_TOOLS:
        for key in CORE_TOOL_REQUIRED_SCHEMA_KEYS:
            assert key in schema, (
                f"Tool {name!r} schema missing key {key!r}"
            )
        assert isinstance(schema["name"], str), (
            f"Tool {name!r} schema.name is not a string"
        )
        assert isinstance(schema["description"], str), (
            f"Tool {name!r} schema.description is not a string"
        )
        assert isinstance(schema["parameters"], dict), (
            f"Tool {name!r} schema.parameters is not a dict"
        )
        # Every tool must have a "type": "object" and "properties"
        assert schema["parameters"].get("type") == "object", (
            f"Tool {name!r} parameters.type is not 'object'"
        )
        assert "properties" in schema["parameters"], (
            f"Tool {name!r} parameters missing 'properties'"
        )


# ── Plugin load ────────────────────────────────────────────────────────────

def test_plugin_imports():
    """The plugin module can be imported without errors."""
    import milimo_hermes_plugin
    assert hasattr(milimo_hermes_plugin, "register")
    assert hasattr(milimo_hermes_plugin, "on_load")
    assert hasattr(milimo_hermes_plugin, "on_unload")


def test_plugin_yaml_manifest():
    """plugin.yaml is well-formed and matches the code."""
    import yaml
    manifest_path = _PLUGIN_DIR / "plugin.yaml"
    assert manifest_path.exists(), f"plugin.yaml not found at {manifest_path}"
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    assert manifest["name"] == "milimo-hermes-plugin"
    assert manifest["entry_point"] == "milimo_hermes_plugin:register"
    assert "milimo-core>=0.1.0" in manifest.get("dependencies", [])
    # The plugin manifest name should match the toolset name
    assert manifest["name"].replace("-plugin", "") == TOOLSET_NAME, (
        f"plugin.yaml name {manifest['name']!r} does not match "
        f"toolset name {TOOLSET_NAME!r}"
    )


# ─── Registration mock test ────────────────────────────────────────────────

class _FakeCtx:
    """Minimal mock for the Hermes PluginContext."""
    def __init__(self):
        self.registered = []

    def register_tool(self, name, toolset, schema, handler, description):
        self.registered.append({
            "name": name,
            "toolset": toolset,
            "schema": schema,
            "handler": handler,
            "description": description,
        })


def test_register_core_tools_registers_all_tools():
    """register_core_tools registers all 6 tools with the correct toolset."""
    from milimo_hermes_plugin.tools import register_core_tools, _CORE_TOOLS

    ctx = _FakeCtx()
    register_core_tools(ctx)

    assert len(ctx.registered) == len(_CORE_TOOLS), (
        f"register_core_tools registered {len(ctx.registered)} tools "
        f"but _CORE_TOOLS has {len(_CORE_TOOLS)}"
    )

    for entry in ctx.registered:
        assert entry["toolset"] == TOOLSET_NAME, (
            f"Tool {entry['name']!r} registered with toolset "
            f"{entry['toolset']!r} but expected {TOOLSET_NAME!r}"
        )
        assert entry["description"] == entry["schema"]["description"], (
            f"Tool {entry['name']!r}: description param does not match "
            f"schema.description"
        )

    registered_names = {e["name"] for e in ctx.registered}
    assert registered_names == set(CORE_TOOL_NAMES), (
        f"Registered tools {registered_names} do not match "
        f"expected {set(CORE_TOOL_NAMES)}"
    )
